import os
import sys
import argparse

from litex.soc.integration.builder import Builder
from litex.build.lattice.trellis import trellis_args, trellis_argdict

from .feather_soc import FeatherSoC
from .builder import FeatherBuilder
# Get argument parsing from here. Simplified compared to litex_boards.
from .args import *

# Build --------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="LiteX SoC on OrangeCrab")
    subparsers = parser.add_subparsers(help="sub-command help")

    parser.add_argument("--build",           action="store_true",  help="Build bitstream")
    parser.add_argument("--load",            action="store_true",  help="Load bitstream")
    parser.add_argument("--toolchain",       default="trellis",    help="FPGA  use, trellis (default) or diamond")
    parser.add_argument("--sys-clk-freq",    default=48e6,         help="System clock frequency (default: 48MHz)")
    parser.add_argument("--revision",        default="0.2",        help="Board Revision: 0.1 or 0.2 (default)")
    parser.add_argument("--device",          default="25F",        help="ECP5 device (default: 25F)")
    parser.add_argument("--sdram-device",    default="MT41K64M16", help="SDRAM device (default: MT41K64M16)")
    parser.add_argument("--no-pac",    action="store_true", help="Skip generating Rust PAC")
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
        # kwargs- SoC args
        # CPU parameters
        cpu_type                 = args.cpu_type,
        cpu_variant              = args.cpu_variant,
        # ROM parameters
        integrated_rom_size      = args.integrated_rom_size,
        # SRAM parameters
        integrated_sram_size     = args.integrated_sram_size,
        # MAIN_RAM parameters
        integrated_main_ram_size = args.integrated_main_ram_size,
        # UART parameters
        uart_baudrate            = args.uart_baudrate,
        uart_fifo_depth          = args.uart_fifo_depth,
        # Timer parameters
        timer_uptime             = args.timer_uptime,
        # SoC SDRAM args
        max_sdram_size    = args.max_sdram_size)

    soc.add_spi_sdcard()

    builder = FeatherBuilder(soc,
        output_dir= args.output_dir,
        compile_software= not args.no_compile_software,
        compile_gateware= not args.no_compile_gateware,
        generate_doc= args.doc,
        generate_pac= not args.no_pac)

    builder_kargs = trellis_argdict(args) if args.toolchain == "trellis" else {}
    builder.build(**builder_kargs, run=args.build)

    if args.load:
        prog = soc.platform.create_programmer()
        prog.load_bitstream(os.path.join(builder.gateware_dir, soc.build_name + ".bit"))

if __name__ == "__main__":
    main()
