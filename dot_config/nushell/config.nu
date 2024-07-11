# Nushell Config File
#
# version = "0.85.0"

alias poly = python C:\Users\niklas.sirch\Projects\hmi\ms\poly\main.py --polymer-root 'C:\Users\niklas.sirch\Projects\hmi\hmi3-polymer-dev\src\web'

def "scoop update all" [exclude: list<string> = [podman]] {
  scoop update
  scoop update ...(
  	scoop status | lines -s | skip 1 | split column ' ' -c  | headers |  drop nth 0
	| filter {|it| $it not-in $exclude})
}

def "git remove not remote" [] {
  git fetch
  git branch -D ...(git branch -vv | find gone | split column ' ' -c | get column2)
}

def "git push --force" [] {
  git push --force-with-lease
}

$env.config = {
    show_banner: false
    bracketed_paste: true # enable bracketed paste, currently useless on windows
    edit_mode: vi
    # shell_integration: false
}

# overlay use nupm/modules/nupm --prefix
use ~/.cache/starship/init.nu
source ~/.cache/carapace/init.nu
source ~/.zoxide.nu

