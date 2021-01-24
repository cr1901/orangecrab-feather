#![no_std]
#![no_main]

extern crate panic_halt;
extern crate riscv_rt;

use riscv_rt::entry;
use litex_pac::{write_reg};
use litex_pac::{leds};

#[entry]
fn main() -> ! {
    let leds = leds::LEDS::take().unwrap();

    write_reg!(leds, leds, OUT, 5);
    // do something here
    loop {}
}
