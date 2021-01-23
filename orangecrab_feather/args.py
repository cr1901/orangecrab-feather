from litex.soc.integration.soc import *
from litex.soc.integration.soc_core import soc_core_argdict
from litex.soc.integration.soc_sdram import soc_sdram_argdict

def builder_args(parser):
    parser.add_argument("--output-dir", default=None,
                        help="base output directory for generated "
                             "source files and binaries")
    parser.add_argument("--no-compile-software", action="store_true",
                        help="do not compile the software, only generate "
                             "build infrastructure")
    parser.add_argument("--no-compile-gateware", action="store_true",
                        help="do not compile the gateware, only generate "
                             "HDL source files and build scripts")
    parser.add_argument("--doc", action="store_true", help="Generate Documentation")


def soc_core_args(parser):
    # CPU parameters
    parser.add_argument("--cpu-type", default="vexriscv",
                        help="select CPU: {}, (default=vexriscv)".format(", ".join(iter(cpu.CPUS.keys()))))
    parser.add_argument("--cpu-variant", default="minimal",
                        help="select CPU variant, (default=minimal)")
    # ROM parameters
    parser.add_argument("--integrated-rom-size", default=0xA000, type=auto_int,
                        help="size/enable the integrated (BIOS) ROM (default=40KB)")
    # SRAM parameters
    parser.add_argument("--integrated-sram-size", default=0x2000, type=auto_int,
                        help="size/enable the integrated SRAM (default=8KB)")
    # MAIN_RAM parameters
    parser.add_argument("--integrated-main-ram-size", default=0x4000, type=auto_int,
                        help="size/enable the integrated main RAM")
    # UART parameters
    parser.add_argument("--uart-baudrate", default=115200, type=auto_int,
                        help="UART baudrate (default=115200)")
    parser.add_argument("--uart-fifo-depth", default=16, type=auto_int,
                        help="UART FIFO depth (default=16)")
    # Timer parameters
    parser.add_argument("--timer-uptime", action="store_true",
                        help="Add an uptime register to the timer (default=False)")


def soc_sdram_args(parser):
    soc_core_args(parser)
    # SDRAM
    parser.add_argument("--max-sdram-size", default=0x40000000, type=auto_int,
                        help="Maximum SDRAM size mapped to the SoC (default=1GB))")
