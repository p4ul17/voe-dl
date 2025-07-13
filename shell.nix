{
  pkgs ? import <nixpkgs> { },
}:

pkgs.mkShell {
  buildInputs = with pkgs; [
    (python3.withPackages (pp: with pp; [
      requests
      beautifulsoup4
      yt-dlp
      wget
    ]))
  ];
}
