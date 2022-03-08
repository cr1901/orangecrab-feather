import os

from litex.soc.integration.builder import Builder
from .pac import *

# Wrapper class to ensure that the Rust PAC is generated without erroring
# because of missing directories and the like.
class FeatherBuilder(Builder):
    def __init__(self, soc,
        generate_pac= True,
        **kwargs):
        self.generate_pac = generate_pac

        Builder.__init__(self, soc, **kwargs)

        # We don't know these dirs until after the Builder is done initializing.
        if self.generate_pac:
            self.rust_dir=os.path.join(self.software_dir, "rust")
            self.csr_svd=os.path.join(self.rust_dir, "csr.svd")

    # If a full software rebuild was requested, the rust_dir will be gone,
    # so recreate it. Right now, I don't expose most paths, so no csr_json
    # or csr_csv.
    def _generate_csr_map(self):
        if self.generate_pac:
            os.makedirs(self.rust_dir, exist_ok=True)

        Builder._generate_csr_map(self)

    # Once the main builder is done, add our Rust PAC if requested.
    def build(self, **kwargs):
        assert self.generate_pac
        Builder.build(self, **kwargs)

        if self.generate_pac:
            pac_builder = PacBuilder(self.soc, self)
            pac_builder.generate()
