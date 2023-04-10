import logging
import sys
import time
import os.path
import numpy
import tango
from tango import DispLevel, AttrWriteType, DevState
from tango.server import attribute, command
import datetime

sys.path.append('../TangoUtils')
from TangoServerPrototype import TangoServerPrototype
import Configuration
import numpy as np
import PyTango
from config_logger import config_logger
from log_exception import log_exception

dt = 10
t0 = time.time()
OFF_PASSWORD = 'topsecret'


class BC_TangoServer(TangoServerPrototype):
    server_version = '1.0'
    server_name = 'Python Control screen shot, dipole magnets and Cs temperature Tango Server'
    device_list = []

    length = attribute(label="length_of_integration", dtype=float,
                       display_level=DispLevel.OPERATOR,
                       access=AttrWriteType.READ_WRITE,
                       unit="s", format="%f",
                       doc="length_of_integration")
    poll = attribute(label="poll", dtype=float,
                     display_level=DispLevel.OPERATOR,
                     access=AttrWriteType.READ_WRITE,
                     unit="s", format="%f",
                     doc="polling time")
    calculate_on = attribute(label="calculate_on", dtype=bool,
                             display_level=DispLevel.OPERATOR,
                             access=AttrWriteType.READ_WRITE,
                             unit="", format="%s",
                             doc="1 - enable calculate, 0 - disable")
    Beam_power = attribute(label="beam_power", dtype=float,
                           display_level=DispLevel.OPERATOR,
                           access=AttrWriteType.READ,
                           unit="kW", format="%f",
                           doc="beam power kW")
    chanx600 = attribute(label="BC1Temp", dtype=PyTango.DevDouble, dformat=PyTango.SPECTRUM, max_dim_x=2048,
                         max_dim_y=2,
                         display_level=DispLevel.OPERATOR, access=AttrWriteType.READ, unit=" oC", format="%f",
                         doc="PET15ai00x")
    chany600 = attribute(label="BC1Time", dtype=PyTango.DevDouble, dformat=PyTango.SPECTRUM, max_dim_x=2048,
                         max_dim_y=2,
                         display_level=DispLevel.OPERATOR, access=AttrWriteType.READ, unit=" s", format="%f",
                         doc="PET15ai00y")
    chanx601 = attribute(label="BC2Temp", dtype=PyTango.DevDouble, dformat=PyTango.SPECTRUM, max_dim_x=2048,
                         max_dim_y=2,
                         display_level=DispLevel.OPERATOR, access=AttrWriteType.READ, unit=" oC", format="%f",
                         doc="PET15ai02x")
    chany601 = attribute(label="BC2Time", dtype=PyTango.DevDouble, dformat=PyTango.SPECTRUM, max_dim_x=2048,
                         max_dim_y=2,
                         display_level=DispLevel.OPERATOR, access=AttrWriteType.READ, unit=" s", format="%f",
                         doc="PET15ai02y")

    def init_device(self):
        self.calc_on = 0
        self.length_of_int = 300.0
        self.poll_time = 0.2
        self.BeamPWR = 0
        super().init_device()
        BC_TangoServer.device_list.append(self)  # global dev=self

    def read_Beam_power(self):
        return self.BeamPWR

    def read_calculate_on(self):
        return self.calc_on == 1

    def write_calculate_on(self, value):
        global s1, s2, tango_Rpet, Temp0
        dt = self.poll_time
        if value == 1:

            try:
                tango_Rpet.poll_attribute(s1, int(dt * 1000))
                time.sleep(0.2)
                Temp0 = tango_Rpet.attribute_history(s1, 1)[0].value * 30 - 15

                tango_Rpet.poll_attribute(s2, int(dt * 1000))
                time.sleep(0.2)
                Temp0 = tango_Rpet.attribute_history(s2, 1)[0].value * 30 - 15
            except:
                print("сбой инициализации полинга ")
                raise
        else:
            try:
                tango_Rpet.stop_poll_attribute(s1)
                tango_Rpet.stop_poll_attribute(s2)
            except:
                print("сбой выключения полинга ")
                raise
        self.calc_on = value

    def read_length(self):
        return self.length_of_int

    def write_length(self, value):
        self.length_of_int = value

    def read_poll(self):
        return self.poll_time

    def write_poll(self, value):
        self.poll_time = value

    def read_chany600(self):
        global chany1000
        return chany1000

    def read_chanx600(self):
        global chanx1000
        return chanx1000

    def read_chany601(self):
        global chany1001
        return chany1001

    def read_chanx601(self):
        global chanx1001
        return chanx1001


sizeS = 0


def next(j, jmax):
    j = (j + 1) % jmax
    return j


jmax = 2048
chany1000 = np.zeros(jmax)
chanx1000 = np.zeros(jmax)


def newshot():
    # global chany1000, j
    global tango_Vasya, last_shot_number
    a = tango_Vasya.shotnumber
    print(a)
    if a != last_shot_number:
        last_shot_number = a
        return 0
    else:
        return 0  # -10<chany1000[j]<10


def looping():
    for dev in BC_TangoServer.device_list:
        # time.sleep(1)
        sleeptime = 1
        global tango_Rpet, Temp0, Temp02
        global chany1000, chanx1000, chany1001, chanx1001, j, j2
        if newshot():
            chany1000 = np.zeros(jmax)
            chanx1000 = np.zeros(jmax)
            chany1001 = np.zeros(jmax)
            chanx1001 = np.zeros(jmax)
            j = -1
            j2 = -1
        global s1
        global to_integrate

        try:
            dt = dev.poll_time
            length = int(sleeptime // dev.poll_time) + 1
            # print(length)
            time.sleep(sleeptime)
            # print(dt)
            try:
                tango_Rpet.is_attribute_polled(s1)
            except:
                time.sleep(1)
            if not tango_Rpet.is_attribute_polled(s1):
                continue
            else:
                tah = tango_Rpet.attribute_history(s1, length)
                # print(length)
                # print(tah[0].value)
                global t0
                # global jmax
                _order = chanx1000.argsort()
                print(np.trapz(chany1000[_order], chanx1000[_order]))
                for c in tah:
                    na = (c.value) - Temp0
                    # na = (c.value)*30-15-Temp0
                    # print(Temp0)
                    nat1 = (c.time.tv_sec)
                    nat2 = c.time.tv_usec
                    nat = (nat1 + nat2 / 1000000) - t0
                    j = next(j, jmax)
                    # print(j, c.time.tv_sec-t0, c.value)
                    chany1000[j] = na
                    chanx1000[j] = nat  # c.time.tv_sec-t0
                    # t0 = np.min(chanx1000)
                # print(chanx1000)

                tah2 = tango_Rpet.attribute_history(s2, length)
                # print(length)
                # print(tah[0].value)
                # global jmax
                _order = chanx1001.argsort()
                print(np.trapz(chany1001[_order], chanx1001[_order]))
                for c in tah2:
                    na = (c.value) - Temp02
                    # na = (c.value) * 30 - 15 - Temp02
                    # print(Temp0)
                    nat1 = (c.time.tv_sec)
                    nat2 = c.time.tv_usec
                    nat = (nat1 + nat2 / 1000000) - t0
                    j2 = next(j2, jmax)
                    # print(j, c.time.tv_sec-t0, c.value)
                    chany1001[j2] = na
                    chanx1001[j2] = nat  # c.time.tv_sec - t0
                    # t0 = np.min(chanx1000)
                # print(chanx1000)


        except:
            print("fail")
            raise


time_lag = 301
last_shot_number = -1
Temp0 = 0
Temp02 = 0
j = -1
j2 = -1
if __name__ == "__main__":
    print(1)

    try:
        # tango_Rpet=tango.DeviceProxy("et7000_server/test/pet24_7026")
        tango_Rpet = tango.DeviceProxy("et7000_server/test/pet17_7018")
        tango_Vasya = tango.DeviceProxy("test/nbi/vasya")
        print(tango_Vasya)
        print("oi")
        # s1="ai00"
        s1 = "ai01"
        s2 = "ai03"
        t0 = time.time()
        j = -1
        j2 = -1
        jmax = 2048
        try:
            Temp0 = tango_Rpet.attribute_history(s1, 1)[0].value
            # Temp0=tango_Rpet.attribute_history(s1, 1)[0].value*30-15
            Temp02 = tango_Rpet.attribute_history(s2, 1)[0].value
            # Temp02 = tango_Rpet.attribute_history(s2, 1)[0].value * 30 - 15
        except:
            Temp0 = tango_Rpet.ai01
            # Temp0 = tango_Rpet.ai00*30-15
            Temp02 = tango_Rpet.ai03
            # Temp02 = tango_Rpet.ai02*30-15
            # raise
        print(Temp0)
        chany1000 = np.zeros(jmax)
        chanx1000 = np.zeros(jmax)
        chany1001 = np.zeros(jmax)
        chanx1001 = np.zeros(jmax)
        print(t0)
        # to_integrate = tango.AttributeProxy("tango/test/1/double_scalar_rww")
    except:
        raise
    BC_TangoServer.run_server(event_loop=looping)
