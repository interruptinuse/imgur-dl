with import <nixpkgs> {};
let
  imgur-dl =
    let
      pname = "imgur-dl";
      version = "0.1";
      inherit (mypython.pkgs) buildPythonApplication;
      inherit (mypython.pkgs) setuptools requests tqdm parsel esprima termcolor;
    in
    buildPythonApplication {
      inherit pname version;

      src = ./.;

      doCheck = false;
      buildInputs = [ setuptools ];
      propagatedBuildInputs = [ requests tqdm parsel esprima termcolor ];
    };
in
mkShell {
  buildInputs = [
    imgur-dl
  ];
}
