#!/usr/bin/env python3

#
# This file was developed using LiteX-Boards as a base.
#
# Copyright (c) Greg Davill <greg.davill@gmail.com>
# Copyright (c) William D. Jones <thor0505@comcast.net>
# SPDX-License-Identifier: BSD-2-Clause

import os
import sys

from migen import *
from migen.genlib.misc import WaitTimer
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex_boards.platforms import orangecrab
from litex.soc.integration.soc_core import *

from litex.soc.cores.clock import *
from litex.soc.cores.uart import UARTPHY, UART
from litex.soc.cores.led import LedChaser
from litex.soc.cores.spi import SPIMaster

from litex.soc.interconnect.csr_eventmanager import *

from litedram.modules import MT41K64M16, MT41K128M16, MT41K256M16, MT41K512M16
from litedram.phy import ECP5DDRPHY

# CRG ---------------------------------------------------------------------------------------------

class _CRG(Module):
    def __init__(self, platform, sys_clk_freq, with_usb_pll=False):
        self.rst = Signal()
        self.clock_domains.cd_por = ClockDomain(reset_less=True)
        self.clock_domains.cd_sys = ClockDomain()

        # # #

        # Clk / Rst
        clk48 = platform.request("clk48")
        rst_n = platform.request("usr_btn", loose=True)
        if rst_n is None: rst_n = 1

        # Power on reset
        por_count = Signal(16, reset=2**16-1)
        por_done  = Signal()
        self.comb += self.cd_por.clk.eq(clk48)
        self.comb += por_done.eq(por_count == 0)
        self.sync.por += If(~por_done, por_count.eq(por_count - 1))

        # PLL
        self.submodules.pll = pll = ECP5PLL()
        self.comb += pll.reset.eq(~por_done | ~rst_n | self.rst)
        pll.register_clkin(clk48, 48e6)
        pll.create_clkout(self.cd_sys, sys_clk_freq)

        # USB PLL
        if with_usb_pll:
            self.clock_domains.cd_usb_12 = ClockDomain()
            self.clock_domains.cd_usb_48 = ClockDomain()
            usb_pll = ECP5PLL()
            self.submodules += usb_pll
            self.comb += usb_pll.reset.eq(~por_done)
            usb_pll.register_clkin(clk48, 48e6)
            usb_pll.create_clkout(self.cd_usb_48, 48e6)
            usb_pll.create_clkout(self.cd_usb_12, 12e6)

        # FPGA Reset (press usr_btn for 1 second to fallback to bootloader)
        reset_timer = WaitTimer(int(48e6))
        reset_timer = ClockDomainsRenamer("por")(reset_timer)
        self.submodules += reset_timer
        self.comb += reset_timer.wait.eq(~rst_n)
        self.comb += platform.request("rst_n").eq(~reset_timer.done)


class _CRGSDRAM(Module):
    def __init__(self, platform, sys_clk_freq, with_usb_pll=False):
        self.rst = Signal()
        self.clock_domains.cd_init     = ClockDomain()
        self.clock_domains.cd_por      = ClockDomain(reset_less=True)
        self.clock_domains.cd_sys      = ClockDomain()
        self.clock_domains.cd_sys2x    = ClockDomain()
        self.clock_domains.cd_sys2x_i  = ClockDomain(reset_less=True)

        # # #

        self.stop  = Signal()
        self.reset = Signal()

        # Clk / Rst
        clk48 = platform.request("clk48")
        rst_n = platform.request("usr_btn", loose=True)
        if rst_n is None: rst_n = 1

        # Power on reset
        por_count = Signal(16, reset=2**16-1)
        por_done  = Signal()
        self.comb += self.cd_por.clk.eq(clk48)
        self.comb += por_done.eq(por_count == 0)
        self.sync.por += If(~por_done, por_count.eq(por_count - 1))

        # PLL
        sys2x_clk_ecsout = Signal()
        self.submodules.pll = pll = ECP5PLL()
        self.comb += pll.reset.eq(~por_done | ~rst_n | self.rst)
        pll.register_clkin(clk48, 48e6)
        pll.create_clkout(self.cd_sys2x_i, 2*sys_clk_freq)
        pll.create_clkout(self.cd_init, 24e6)
        self.specials += [
            Instance("ECLKBRIDGECS",
                i_CLK0   = self.cd_sys2x_i.clk,
                i_SEL    = 0,
                o_ECSOUT = sys2x_clk_ecsout),
            Instance("ECLKSYNCB",
                i_ECLKI = sys2x_clk_ecsout,
                i_STOP  = self.stop,
                o_ECLKO = self.cd_sys2x.clk),
            Instance("CLKDIVF",
                p_DIV     = "2.0",
                i_ALIGNWD = 0,
                i_CLKI    = self.cd_sys2x.clk,
                i_RST     = self.reset,
                o_CDIVX   = self.cd_sys.clk),
            AsyncResetSynchronizer(self.cd_sys,   ~pll.locked | self.reset),
            AsyncResetSynchronizer(self.cd_sys2x, ~pll.locked | self.reset),
        ]

        # USB PLL
        if with_usb_pll:
            self.clock_domains.cd_usb_12 = ClockDomain()
            self.clock_domains.cd_usb_48 = ClockDomain()
            usb_pll = ECP5PLL()
            self.submodules += usb_pll
            self.comb += usb_pll.reset.eq(~por_done)
            usb_pll.register_clkin(clk48, 48e6)
            usb_pll.create_clkout(self.cd_usb_48, 48e6)
            usb_pll.create_clkout(self.cd_usb_12, 12e6)

        # FPGA Reset (press usr_btn for 1 second to fallback to bootloader)
        reset_timer = WaitTimer(int(48e6))
        reset_timer = ClockDomainsRenamer("por")(reset_timer)
        self.submodules += reset_timer
        self.comb += reset_timer.wait.eq(~rst_n)
        self.comb += platform.request("rst_n").eq(~reset_timer.done)

# FeatherSoC ------------------------------------------------------------------------------------------

class FeatherSoC(SoCCore):
    def __init__(self, revision="0.2", device="25F", sdram_device="MT41K64M16",
                 sys_clk_freq=int(48e6), toolchain="trellis", **kwargs):
        platform = orangecrab.Platform(revision=revision, device=device, toolchain=toolchain)
        platform.add_extension(orangecrab.feather_serial)
        platform.add_extension(orangecrab.feather_spi)
        platform.add_extension(orangecrab.feather_i2c)

        # Serial -----------------------------------------------------------------------------------
        # Defaults to USB ACM through ValentyUSB.
        sys.path.append("deps/valentyusb")

        # SoCCore ----------------------------------------------------------------------------------
        SoCCore.__init__(self, platform, sys_clk_freq,
            uart_name      = "usb_acm",
            ident          = "FeatherSoC on OrangeCrab (using LiteX)",
            ident_version  = True,
            **kwargs)

        # CRG --------------------------------------------------------------------------------------
        crg_cls = _CRGSDRAM if not self.integrated_main_ram_size else _CRG
        self.submodules.crg = crg_cls(platform, sys_clk_freq, True)

        # DDR3 SDRAM -------------------------------------------------------------------------------
        if not self.integrated_main_ram_size:
            available_sdram_modules = {
                "MT41K64M16":  MT41K64M16,
                "MT41K128M16": MT41K128M16,
                "MT41K256M16": MT41K256M16,
                "MT41K512M16": MT41K512M16,
            }
            sdram_module = available_sdram_modules.get(sdram_device)

            ddram_pads = platform.request("ddram")
            self.submodules.ddrphy = ECP5DDRPHY(
                pads         = ddram_pads,
                sys_clk_freq = sys_clk_freq,
                cmd_delay    = 0 if sys_clk_freq > 64e6 else 100,
                dm_remapping = {0:1, 1:0})
            self.ddrphy.settings.rtt_nom = "disabled"
            self.add_csr("ddrphy")
            if hasattr(ddram_pads, "vccio"):
                self.comb += ddram_pads.vccio.eq(0b111111)
            if hasattr(ddram_pads, "gnd"):
                self.comb += ddram_pads.gnd.eq(0)
            self.comb += self.crg.stop.eq(self.ddrphy.init.stop)
            self.comb += self.crg.reset.eq(self.ddrphy.init.reset)
            self.add_sdram("sdram",
                phy                     = self.ddrphy,
                module                  = sdram_module(sys_clk_freq, "1:2"),
                origin                  = self.mem_map["main_ram"],
                size                    = kwargs.get("max_sdram_size", 0x40000000),
                l2_cache_size           = kwargs.get("l2_size", 8192),
                l2_cache_min_data_width = kwargs.get("min_l2_data_width", 128),
                l2_cache_reverse        = True
            )

        # Leds -------------------------------------------------------------------------------------
        self.submodules.leds = LedChaser(
            pads         = platform.request_all("user_led"),
            sys_clk_freq = sys_clk_freq)
        self.add_csr("leds")

        # Feather Serial core
        self.submodules.feather_uart_phy = UARTPHY(
            pads     = self.platform.request("serial"),
            clk_freq = self.sys_clk_freq,
            baudrate = 115200)
        self.submodules.feather_uart = ResetInserter()(UART(self.feather_uart_phy,
            tx_fifo_depth = 16,
            rx_fifo_depth = 16))

        self.csr.add("feather_uart_phy", use_loc_if_exists=True)
        self.csr.add("feather_uart", use_loc_if_exists=True)
        self.irq.add("feather_uart", use_loc_if_exists=True)

        # SPI core
        self.submodules.spi = SPIMaster(
            pads = None,
            data_width = 8,
            sys_clk_freq = self.sys_clk_freq,
            spi_clk_freq = 12e6)

        spi_pads = platform.request("spi")
        self.comb += [
            spi_pads.clk.eq(self.spi.pads.clk),
            spi_pads.mosi.eq(self.spi.pads.mosi),
            self.spi.pads.miso.eq(spi_pads.miso)
        ]

        self.csr.add("spi", use_loc_if_exists=True)

        self.spi.submodules.ev = EventManager()
        self.spi.ev.eot = EventSourceProcess()
        self.spi.ev.finalize()
        self.comb += self.spi.ev.eot.trigger.eq(~self.spi.irq)

        self.irq.add("spi", use_loc_if_exists=True)

        # I2C core
        sys.path.append("deps/gateware")
        from gateware.i2c.core import RTLI2C

        self.submodules.betrusted_i2c = RTLI2C(platform, platform.request("i2c"))
        self.csr.add("betrusted_i2c", use_loc_if_exists=True)
        self.irq.add("betrusted_i2c", use_loc_if_exists=True)
