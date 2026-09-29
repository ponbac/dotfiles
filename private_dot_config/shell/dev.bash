# Shared interactive Bash conveniences. Source AFTER host/package startup.
# Do not add credentials, runtime PATH overrides, installers, or mise use here.
[[ $- == *i* ]] || return 0
[[ ${_PONBAC_DEV_SHELL_LOADED:-} == 1 ]] && return 0
_PONBAC_DEV_SHELL_LOADED=1

alias gs='git status'
alias gd='git diff'
alias gl='git log --oneline --graph --decorate'

# Omarchy already initializes Starship. Never install it or initialize twice.
if [[ ${TERM:-dumb} != dumb && ${STARSHIP_SHELL:-} != bash ]] &&
   command -v starship >/dev/null 2>&1; then
  eval "$(starship init bash)"
fi

# Runtime activation remains host-owned: Omarchy's packaged init/session setup
# and Ubuntu's existing setup must retain their PATH and version precedence.
