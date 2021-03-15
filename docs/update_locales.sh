#!/usr/bin/env sh

# gen .pot files
make gettext
# update .po files for existing langs / create new
sphinx-intl update -p _build/locale -l ru
