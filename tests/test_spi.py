"""Tests for pslab.bus.spi.

When integration testing, the PSLab's logic analyzer and PWM output are used to
verify the function of the SPI bus. Before running the integration tests, connect:
    SCK    -> LA1
    SDO    -> LA2
    SDI    -> SQ1
    SPI.CS -> LA3
"""

import pytest

from pslab.bus.spi import SPIMaster, SPISlave
from pslab.instrument.logic_analyzer import LogicAnalyzer
from pslab.instrument.waveform_generator import PWMGenerator
from pslab.serial_handler import SerialHandler

WRITE_DATA8 = 0b10100101
WRITE_DATA16 = 0xAA55
SCK = "LA1"
SDO = "LA2"
SDI = "SQ1"
CS = "LA3"
MICROSECONDS = 1e-6
RELTOL = 0.05
# Number of expected logic level changes.
CS_START = 1
CS_STOP = 1
SCK_WRITE8 = 16
SCK_WRITE16 = 2 * 16
SDO_WRITE_DATA8 = 8
SDO_WRITE_DATA16 = 16


@pytest.fixture
def master(handler: SerialHandler) -> SPIMaster:
    handler._logging = True
    spi_master = SPIMaster(device=handler)
    yield spi_master
    spi_master.set_parameters()


@pytest.fixture
def slave(handler: SerialHandler) -> SPISlave:
    handler._logging = True
    return SPISlave(device=handler)


@pytest.fixture
def la(handler: SerialHandler) -> LogicAnalyzer:
    handler._logging = True
    return LogicAnalyzer(handler)


@pytest.fixture
def pwm(handler: SerialHandler) -> PWMGenerator:
    handler._logging = True
    return PWMGenerator(handler)


def test_set_parameter_frequency(la: LogicAnalyzer, master: SPIMaster, slave: SPISlave):
    # frequency 166666.66666666666
    ppre = 0
    spre = 2
    master.set_parameters(primary_prescaler=ppre, secondary_prescaler=spre)
    la.capture(1, block=False)
    slave.write8(0)
    la.stop()
    (sck,) = la.fetch_data()
    write_start = sck[0]
    write_stop = sck[-2]  # Output data on rising edge only (in mode 0)
    start_to_stop = 7
    period = (write_stop - write_start) / start_to_stop
    assert (period * MICROSECONDS) ** -1 == pytest.approx(master._frequency, rel=RELTOL)


@pytest.mark.parametrize("ckp", [0, 1])
def test_set_parameter_clock_polarity(
    la: LogicAnalyzer, master: SPIMaster, slave: SPISlave, ckp: int
):
    master.set_parameters(CKP=ckp)
    assert la.get_states()[SCK] == bool(ckp)


@pytest.mark.parametrize("cke", [0, 1])
def test_set_parameter_clock_edge(
    la: LogicAnalyzer, master: SPIMaster, slave: SPISlave, cke: int
):
    master.set_parameters(CKE=cke)
    la.capture(2, block=False)
    slave.write8(WRITE_DATA8)
    la.stop()
    (sck, sdo) = la.fetch_data()
    idle_to_active = sck[0]
    first_bit = sdo[0]
    # Serial output data changes on transition
    # {0: from Idle clock state to active state (first event before data change),
    #  1: from active clock state to Idle state (data change before first event)}.
    assert first_bit < idle_to_active == bool(cke)


@pytest.mark.parametrize("smp", [0, 1])
def test_set_parameter_smp(
    la: LogicAnalyzer, master: SPIMaster, slave: SPISlave, pwm: PWMGenerator, smp: int
):
    master.set_parameters(SMP=smp)
    # TODO


def test_chip_select(la: LogicAnalyzer, slave: SPISlave):
    assert la.get_states()[CS]

    la.capture(CS, block=False)
    slave._start()
    slave._stop()
    la.stop()
    (cs,) = la.fetch_data()
    assert len(cs) == (CS_START + CS_STOP)


def test_write8(la: LogicAnalyzer, slave: SPISlave):
    la.capture(3, block=False)
    slave.write8(WRITE_DATA8)
    la.stop()
    (sck, sdo, cs) = la.fetch_data()

    assert len(cs) == (CS_START + CS_STOP)
    assert len(sck) == SCK_WRITE8
    assert len(sdo) == SDO_WRITE_DATA8


def test_write16(la: LogicAnalyzer, slave: SPISlave):
    la.capture(3, block=False)
    slave.write16(WRITE_DATA16)
    la.stop()
    (sck, sdo, cs) = la.fetch_data()

    assert len(cs) == (CS_START + CS_STOP)
    assert len(sck) == SCK_WRITE16
    assert len(sdo) == SDO_WRITE_DATA16


# TODO test_{transfer,read}{8,16}
