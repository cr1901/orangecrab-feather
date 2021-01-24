import os
import subprocess
import shutil
from string import Template

class PacBuilder:
    # Exclude [dependencies] line, as it will already exist.
    DEPS = """$rt_crate = "$rt_crate_version"
$cpu_crate = "$cpu_crate_version"

[build-dependencies]
svd2ral = { git = "https://github.com/Disasm/svd2ral" }
"""

    BUILD_RS = """use std::fs::{self, File};
use std::io::Read;
use std::path::{Path, PathBuf};
use std::env;
use svd2ral::{generate, AddressSize};

const SVD_FILE: &str = "$svd_file";
const REGIONS_FILE: &str = "$regions";

fn main() {
    // Put the memory definitions somewhere the linker can find it
    let out_dir = PathBuf::from(env::var("OUT_DIR").unwrap());
    let dest_path = Path::new(&out_dir);
    fs::copy(REGIONS_FILE, &dest_path.join("regions.ld")).unwrap();

    let xml = &mut String::new();
    File::open(SVD_FILE).unwrap().read_to_string(xml).unwrap();

    let crate_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());
    generate(&xml, crate_dir.join("src"), AddressSize::U32, &["IDENTIFIER_MEM"]).unwrap();

    println!("cargo:rustc-link-search={}", out_dir.display());
    println!("cargo:rerun-if-changed={}", REGIONS_FILE);
    println!("cargo:rerun-if-changed={}", SVD_FILE);
    println!("cargo:rerun-if-changed=build.rs");
    println!("cargo:rerun-if-env-changed=FORCE");
}
"""

    LIB_RS="""#![no_std]

use $cpu_crate as arch;

mod register;
pub use crate::register::{RORegister, UnsafeRORegister};
pub use crate::register::{WORegister, UnsafeWORegister};
pub use crate::register::{RWRegister, UnsafeRWRegister};

mod soc;
pub use soc::*;
"""

    def __init__(self, soc, builder):
        self.soc = soc
        self.software_dir = builder.software_dir
        self.rust_dir = os.path.join(builder.software_dir, "rust")

    def generate(self):
        if self.soc.cpu_type in ["vexriscv"]:
            rt_crate = "riscv-rt"
            rt_crate_version = "0.8.0"
            cpu_crate = "riscv"
            cpu_crate_version = "0.6.0"
        else:
            raise ValueError(f"Unsupported CPU {self.soc.cpu_type}")

        cwd = os.getcwd()
        os.chdir(self.rust_dir)

        if not os.path.exists("litex-pac"):
            os.makedirs("litex-pac")

        os.chdir("litex-pac")

        if not os.path.exists("Cargo.toml"):
            subprocess.check_call(["cargo", "init", "--lib", "--vcs", "none", "."])
            with open("Cargo.toml", "a+") as f:
                f.seek(0, 2)
                f.write(Template(PacBuilder.DEPS)
                    .substitute(rt_crate=rt_crate,
                                rt_crate_version=rt_crate_version,
                                cpu_crate=cpu_crate,
                                cpu_crate_version=cpu_crate_version))

        with open(os.path.join("build.rs"), "w") as f:
            f.write(Template(PacBuilder.BUILD_RS)
                .substitute(regions=os.path.join(self.software_dir, "include", "generated", "regions.ld"),
                            svd_file=os.path.join(self.rust_dir, "csr.svd")))

        with open(os.path.join("src", "lib.rs"), "w") as f:
            f.write(Template(PacBuilder.LIB_RS)
                .substitute(cpu_crate=cpu_crate))

        os.chdir(cwd)
