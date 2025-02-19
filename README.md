# dconf-fancy-load

dconf-fancy-load is like `dconf load`, but with more features to make it easier
to manage [dconf](https://gitlab.gnome.org/GNOME/dconf) settings from your
dotfiles. And gsettings too, if you use its dconf backend.

## Installation

1.  Install [pipx](https://pypa.github.io/pipx/).
1.  `pipx install git+https://github.com/dseomn/dconf-fancy-load.git`

## Configuration

By default, dconf-fancy-load loads all `*.ini.jinja` files in
`~/.config/dconf-fancy-load/`. The format is very similar to that used by `dconf
dump` and `dconf load`, but with a few differences:

*   Directories and keys can be *selectively* reset using the special `/reset`
    option[^1]. That way you can experiment with different settings
    interactively, then put the ones you want into your dotfiles once you've
    decided on them, then be confident that the settings on the computer you
    experimented on won't be different from other computers. For example:

    ```INI
    [org/gnome/shell]
    # Reset everything under /org/gnome/shell/ that isn't specified here.
    /reset=true
    # However, neither set command-history in dotfiles, nor reset it when
    # resetting its parent directory.
    command-history/reset=false
    ```

[^1]: dconf seems to [accept almost anything other than
    `/`](https://gitlab.gnome.org/GNOME/dconf/-/blob/main/common/dconf-paths.c)
    in key and directory names, so I picked `/option=foo` as a way to specify
    directory options and `key/option=foo` for key options.

*   The key files support newlines in values (which are converted to spaces), so
    you can format larger values more readably:

    ```INI
    [org/gnome/shell]
    favorite-apps=
      [
        'org.gnome.Ptyxis.desktop',
        'firefox.desktop',
        'thunderbird.desktop',
        'io.github.quodlibet.QuodLibet.desktop',
        'org.gnome.Nautilus.desktop'
      ]
    ```

*   Files are rendered with
    [jinja](https://jinja.palletsprojects.com/en/stable/templates/) and can
    access environment variables. So if you have different home directories on
    different computers but always want the same background image in GNOME, you
    can use HOME in the template:

    ```INI
    [org/gnome/desktop/background]
    picture-uri='file://{{ env['HOME'] }}/Pictures/background.png'
    ```

If you find a file that works with `dconf load` but does not work with
dconf-fancy-load (after escaping jinja directives if needed), please file a bug.

My personal dotfiles repo has [more
examples](https://github.com/dseomn/dotfiles/tree/public/.config/dconf-fancy-load)
of how to use dconf-fancy-load.

## Running

If you want to see what dconf-fancy-load would do without making any changes:

```
dconf-fancy-load --dry-run
```

When you're ready to apply the changes:

```
dconf-fancy-load
```
