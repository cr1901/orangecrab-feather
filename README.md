# `orangecrab_feather`

`orangecrab_feather` is a [LiteX](https://github.com/enjoy-digital/litex) SoC
meant to make it easy to write firmware to target other [Feathers](https://github.com/enjoy-digital/litex)
and FeatherWings. Peripherals include:

* USB serial
* Separate UART for Feather pins
* SD Card via SPI controller
* Separate SPI controller for Feather pins
* I2C core
* Timer
* RGB LED
* Pushbutton which will reset CPU, _and_ load bootloader bitstream if pressed
  for 1 second.

## Quick Start

Prerequisites:

```
git clone https://github.com/cr1901/orangecrab-feather.git
cd orangecrab-feather
git submodule update --init
```

_Make sure `riscv64-unknown-elf-gcc` is on the path._

### Build a SoC

Run commands from the root of this repo. _Make sure the OrangeCrab is running
the bootloader bitstream (keep push button pressed while connecting USB power)._

Small SoC (defaults to 16kB of block RAM, no DRAM, shorter build time):
```
python -m orangecrab_feather --build --load --ecppack-compress
```

DRAM SoC (128MB of DRAM, longer build/init time):
```
python -m orangecrab_feather --integrated-main-ram-size=0 --build --load --ecppack-compress
```

* To recompile software and regenerate files only, remove `--build` and `--load`.
  _This is the default if no options are provided_.
* To regenerate files only, add `--no-compile-software`.
* I don't actually remember what `--no-compile-gateware` does. I included it
  because LiteX has it, but I think the `--build` option overrides all its uses.
* To skip Rust PAC generation, add `--no-pac`. PAC generation is not affected
  by any of the 4 above options.
* To generate documentation, use `--doc`. Doc generation is not
  affected by any of the 4 options above `--no-pac`.

### Build Demo Firmware

Change directory to the `./demo` directory in the root of this repo; the Rust
crate depends on a PAC being available under `build/gsd_orangecrab/software/rust`.
_Make sure the OrangeCrab is running the SoC bitstream_.

If nothing happens during the `litex_term` step, press the push button while
the SoC bitstream is loaded _for less than one second_. The LiteX BIOS will
then try to reread your program payload over USB serial.

```
cargo build --target riscv32i-unknown-none-elf
riscv64-unknown-elf-objcopy -O binary target/riscv32i-unknown-none-elf/debug/demo target/riscv32i-unknown-none-elf/debug/demo.bin
litex_term --kernel target/riscv32i-unknown-none-elf/debug/demo.bin /path/to/serial/port
```

## TODO/Known Issues.

* Inject `--freq 38.8` into `ecppack` options with LiteX patch.
* Investigate removing hardcoded paths to PAC and `memory.x`.
  * LiteX `Builder` has a `memory_x` option.
  * Removing a hardcoded path is from `Cargo.toml` to PAC is probably harder.
* Add [ADC](https://github.com/orangecrab-fpga/orangecrab-examples/blob/main/litex/modules/analog.py)
  core.
* Add GPIO core (LiteX's should be fine?).
* SoC will hang if until USB serial port is open. Investigate `add_auto_tx_flush`
  for the ValentyUSB core.
* Generating docs on Windows fails pending `sphinx-wavedrom` [fixes](https://github.com/bavovanachte/sphinx-wavedrom/issues/36).
