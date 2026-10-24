"""Minimal dialogs for the TBIM commands (Windows Forms: IronPython and CPython).

pyrevit.forms is not available in every pyRevit engine. With ``"dialogs": false``
in tbim_settings.json (automation) no dialog is shown: the answer is read from
the ``"choices"`` of the settings ({key: value}) or the default is used.
"""
from tbim import paths


def ask_text(key, title, prompt, default=""):
    """Ask for a line of text. Return None if cancelled."""
    settings = paths.read_settings()
    if not settings.get("dialogs", True):
        return settings.get("choices", {}).get(key, default)

    import clr
    clr.AddReference("System.Windows.Forms")
    clr.AddReference("System.Drawing")
    from System.Drawing import Point, Size
    from System.Windows.Forms import Button, DialogResult, Form, FormBorderStyle, FormStartPosition, Label, TextBox

    form = Form()
    form.Text = "TBIM - " + title
    form.Size = Size(460, 150)
    form.StartPosition = FormStartPosition.CenterScreen
    form.FormBorderStyle = FormBorderStyle.FixedToolWindow
    label = Label()
    label.Text = prompt
    label.Location, label.Size = Point(10, 10), Size(420, 20)
    box = TextBox()
    box.Text = default or ""
    box.Location, box.Size = Point(10, 34), Size(420, 24)
    form.Controls.Add(label)
    form.Controls.Add(box)
    for i, (text, result) in enumerate((("Cancel", DialogResult.Cancel), ("OK", DialogResult.OK))):
        button = Button()
        button.Text, button.DialogResult = text, result
        button.Size, button.Location = Size(90, 28), Point(340 - 100 * i, 70)
        form.Controls.Add(button)
        if result == DialogResult.OK:
            form.AcceptButton = button
        else:
            form.CancelButton = button
    return box.Text if form.ShowDialog() == DialogResult.OK else None


def select(key, title, options, default=None):
    """Pick one of ``options`` (strings). Return None if cancelled."""
    options = list(options)
    if not options:
        return None
    default = default if default in options else options[0]
    settings = paths.read_settings()
    if not settings.get("dialogs", True):
        choice = settings.get("choices", {}).get(key)
        return choice if choice in options else default

    import clr
    clr.AddReference("System.Windows.Forms")
    clr.AddReference("System.Drawing")
    from System.Drawing import Point, Size
    from System.Windows.Forms import (
        AnchorStyles,
        Button,
        DialogResult,
        DockStyle,
        Form,
        FormBorderStyle,
        FormStartPosition,
        ListBox,
        Panel,
    )

    form = Form()
    form.Text = "TBIM - " + title
    form.Size = Size(460, 420)
    form.StartPosition = FormStartPosition.CenterScreen
    form.FormBorderStyle = FormBorderStyle.SizableToolWindow

    listbox = ListBox()
    listbox.Dock = DockStyle.Fill
    for option in options:
        listbox.Items.Add(option)
    listbox.SelectedIndex = options.index(default)

    def accept(sender, args):
        form.DialogResult = DialogResult.OK  # closes the modal form
    listbox.DoubleClick += accept

    buttons = Panel()
    buttons.Dock = DockStyle.Bottom
    buttons.Height = 40
    for i, (text, result) in enumerate((("Cancel", DialogResult.Cancel), ("OK", DialogResult.OK))):
        button = Button()
        button.Text = text
        button.DialogResult = result
        button.Size = Size(90, 28)
        button.Location = Point(form.ClientSize.Width - 100 * (i + 1), 6)
        button.Anchor = AnchorStyles.Right | AnchorStyles.Top
        buttons.Controls.Add(button)
        if result == DialogResult.OK:
            form.AcceptButton = button
        else:
            form.CancelButton = button

    form.Controls.Add(listbox)
    form.Controls.Add(buttons)
    if form.ShowDialog() != DialogResult.OK or listbox.SelectedItem is None:
        return None
    return str(listbox.SelectedItem)
