import os
import sys
import argparse

from litex.soc.integration.builder import *
from litex.soc.integration.soc_core import *
from litex.soc.integration.soc_sdram import *
from litex.build.lattice.trellis import trellis_args, trellis_argdict

from .feather_soc import FeatherSoC

# Build --------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LiteX SoC on OrangeCrab")
    parser.add_argument("--build",           action="store_true",  help="Build bitstream")
    parser.add_argument("--load",            action="store_true",  help="Load bitstream")
    parser.add_argument("--toolchain",       default="trellis",    help="FPGA  use, trellis (default) or diamond")
    parser.add_argument("--sys-clk-freq",    default=48e6,         help="System clock frequency (default: 48MHz)")
    parser.add_argument("--revision",        default="0.2",        help="Board Revision: 0.1 or 0.2 (default)")
    parser.add_argument("--device",          default="25F",        help="ECP5 device (default: 25F)")
    parser.add_argument("--sdram-device",    default="MT41K64M16", help="SDRAM device (default: MT41K64M16)")
    parser.add_argument("--with-spi-sdcard", action="store_true",  help="Enable SPI-mode SDCard support")
    builder_args(parser)
    soc_sdram_args(parser)
    trellis_args(parser)
    args = parser.parse_args()

    soc = FeatherSoC(
        toolchain    = args.toolchain,
        revision     = args.revision,
        device       = args.device,
        sdram_device = args.sdram_device,
        sys_clk_freq = int(float(args.sys_clk_freq)),
        **soc_sdram_argdict(args))
    if args.with_spi_sdcard:
        soc.add_spi_sdcard()

    builder = Builder(soc, **builder_argdict(args))
    builder_kargs = trellis_argdict(args) if args.toolchain == "trellis" else {}
    builder.build(**builder_kargs, run=args.build)

    if args.load:
        prog = soc.platform.create_programmer()
        prog.load_bitstream(os.path.join(builder.gateware_dir, soc.build_name + ".bit"))

if __name__ == "__main__":
    main()
