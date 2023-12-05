{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-23.11";
    devenv.url = "github:cachix/devenv";
    poetry2nix.url = "github:nix-community/poetry2nix";
    poetry2nix.inputs.nixpkgs.follows = "nixpkgs";
  };

  nixConfig = {
    extra-trusted-public-keys = "devenv.cachix.org-1:w1cLUi8dv3hnoSPGAuibQv+f9TZLr6cv/Hm9XgU50cw=";
    extra-substituters = "https://devenv.cachix.org";
  };

  outputs = { self, nixpkgs, devenv, systems, poetry2nix, ... } @ inputs:
    {
      packages."x86_64-linux" = 
          let
            pkgs = nixpkgs.legacyPackages."x86_64-linux";
            inherit (poetry2nix.lib.mkPoetry2Nix {inherit pkgs;}) mkPoetryApplication;
            app = mkPoetryApplication { projectDir = ./.;
            };
          in
          {
            bga-match-maker = app;
            default = app; 
          };

      devShells."x86_64-linux" = 
          let pkgs = nixpkgs.legacyPackages."x86_64-linux";
          in
          {
            default = devenv.lib.mkShell {
              inherit inputs pkgs;
              modules = [
                {
                  languages.python = {
                    enable = true;
                    poetry.enable = true;
                  };
                }
              ];
            };
          };
};
}
