# typing-reader-cli

 A cli typing trainer that helps you learn typing while reading your favourite books.

## Run

Add a books folder in the project root and run the command from the project root:

```powershell
python -m app.main .\[books folder]
```

## Runtime Config

The UI can be customized by editing `typing-reader.conf`.

Search order for the config file:

1. The path passed with `--config`
2. `typing-reader.conf` in the current working directory
3. A `.conf` file next to the running script or executable
4. `typing-reader.conf` in the project root

Example:

```powershell
python -m app.main .\books --config .\typing-reader.conf
```

Supported options:

```ini
[app]
library_path = books
width = 80
idle_timeout_seconds = 10

[ui]
show_header = true
show_footer = true
screen_align = center top
screen_background =
content_border = round $accent
content_padding = 1 2
content_background =
content_text =
status_padding = 1 2
status_background =
status_text =
tick_interval_seconds = 0.1
title_template = {book} / {chapter}
choice_marker = >
choice_help_text = Use Up/Down and Enter. Esc goes back.
choice_title_style = bold
choice_selected_style = bold cyan
choice_help_style = dim
idle_message = Idle: WPM is paused. Press any key to continue.
summary_title = Session Summary
summary_continue_prompt = Press any key to continue. Esc or Ctrl+C quits.
summary_title_style = bold
summary_prompt_style = yellow

[styles]
correct = bold green
incorrect = bold red
pending = grey50
cursor = reverse bold
idle = yellow
done = bold green
```

Config options:
- `library_path` points to the folder containing your book folders.
- `width` controls the render width used by the session view.
- `idle_timeout_seconds` controls when the idle screen appears and WPM pauses.
- `tick_interval_seconds` controls how often the Textual app refreshes idle state.
- `title_template` controls the text shown at the top of the typing session and status area.
- `screen_background` changes the background color of the whole Textual screen.
- `content_background` changes the background color of the typing area.
- `content_text` changes the base text color of the typing area.
- `status_background` changes the background color of the status area.
- `status_text` changes the base text color of the status area.
- `choice_marker` changes the prefix used for the selected book or chapter in the chooser screens.
- `choice_help_text` changes the helper line shown under the chooser screens.
- `choice_title_style` changes the title/prompt style on chooser screens.
- `choice_selected_style` changes the highlighted item style on chooser screens.
- `choice_help_style` changes the help text style on chooser screens.
- `idle_message` changes the pause message shown while the timer is idle.
- `summary_title` changes the heading on the summary screen.
- `summary_continue_prompt` changes the prompt shown on the summary screen.
- `summary_title_style` changes the heading style on the summary screen.
- `summary_prompt_style` changes the prompt style on the summary screen.
- The style values are Textual/Rich style strings, so you can tune colors and emphasis freely.
- `cursor` controls the current-character highlight, which is rendered as a block-style focus marker in the typing view.
