import gi
import os
from datetime import datetime
from pathlib import Path

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, Gio

class ClipboardManager(Gtk.Window):
    def __init__(self):
        super().__init__(title="Clipboard Manager")
        self.set_default_size(800, 600)

        # Directorio temporal para guardar imágenes copiadas
        self.temp_dir = Path("/tmp/clipboard_manager")
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # Crear lista para almacenar el historial del portapapeles
        self.clipboard_history = []

        # Conectar al portapapeles
        self.clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.clipboard.connect("owner-change", self.on_clipboard_change)

        # Configuración de la interfaz
        self.setup_ui()

    def setup_ui(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add(vbox)

        # Barra de búsqueda
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("Buscar en el historial...")
        self.search_entry.connect("changed", self.on_search)
        clear_button = Gtk.Button.new_from_icon_name("edit-clear", Gtk.IconSize.BUTTON)
        clear_button.connect("clicked", self.on_clear_search)
        search_box.pack_start(self.search_entry, True, True, 0)
        search_box.pack_start(clear_button, False, False, 0)
        vbox.pack_start(search_box, False, False, 0)

        # Configuración del TreeView
        self.tree_store = Gtk.ListStore(str, str, str, Gdk.Texture, str)  # Texto, Tipo, Fecha, Icono, Ruta
        self.tree_view = Gtk.TreeView(model=self.tree_store)

        renderer_icon = Gtk.CellRendererPixbuf()
        column_icon = Gtk.TreeViewColumn("", renderer_icon, pixbuf=3)
        self.tree_view.append_column(column_icon)

        renderer_text = Gtk.CellRendererText()
        column_text = Gtk.TreeViewColumn("Contenido", renderer_text, text=0)
        self.tree_view.append_column(column_text)

        renderer_type = Gtk.CellRendererText()
        column_type = Gtk.TreeViewColumn("Tipo", renderer_type, text=1)
        self.tree_view.append_column(column_type)

        renderer_date = Gtk.CellRendererText()
        column_date = Gtk.TreeViewColumn("Fecha y Hora", renderer_date, text=2)
        self.tree_view.append_column(column_date)

        self.tree_view.connect("row-activated", self.on_row_activated)
        self.tree_view.connect("button-press-event", self.on_right_click)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.add(self.tree_view)
        vbox.pack_start(scroll, True, True, 0)

    def on_clipboard_change(self, clipboard, event):
        """Detectar cambios en el portapapeles y agregar al historial."""
        text = self.clipboard.wait_for_text()
        image = self.clipboard.wait_for_image()

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        icon = None

        if text:
            self.add_to_history(text, "Texto", timestamp, None)
        elif image:
            file_path = self.save_image_to_temp(image)
            icon = self.get_icon("image-x-generic")
            self.add_to_history("Imagen copiada", "Imagen", timestamp, icon, file_path)

    def add_to_history(self, content, content_type, timestamp, icon, file_path=None):
        """Agregar un elemento al historial del portapapeles."""
        self.clipboard_history.append((content, content_type, timestamp, file_path))
        if content_type == "Texto":
            icon = self.get_icon("text-x-generic")
        self.tree_store.append([content[:50], content_type, timestamp, icon, file_path or ""])

    def save_image_to_temp(self, image):
        """Guardar una imagen del portapapeles en un archivo temporal."""
        file_path = self.temp_dir / f"clipboard_image_{len(self.clipboard_history)}.png"
        image.savev(str(file_path), "png", [], [])
        return str(file_path)

    def get_icon(self, icon_name):
        """Obtener un ícono representativo del sistema."""
        theme = Gtk.IconTheme.get_default()
        try:
            return theme.load_icon(icon_name, 32, 0)
        except:
            return None

    def on_row_activated(self, tree_view, path, column):
        """Copiar automáticamente el contenido seleccionado al portapapeles."""
        model = tree_view.get_model()
        row = model[path]
        content_type = row[1]
        content = row[0]
        file_path = row[4]

        if content_type == "Texto":
            self.clipboard.set_text(content, -1)
        elif content_type == "Imagen" and file_path:
            pixbuf = Gdk.pixbuf_new_from_file(file_path)
            self.clipboard.set_image(pixbuf)

    def on_right_click(self, tree_view, event):
        """Mostrar menú contextual al hacer clic derecho."""
        if event.button == 3:  # Clic derecho
            path_info = tree_view.get_path_at_pos(int(event.x), int(event.y))
            if path_info:
                path, _, _, _ = path_info
                model = tree_view.get_model()
                row = model[path]

                menu = Gtk.Menu()

                open_with_item = Gtk.MenuItem(label="Abrir con...")
                open_with_item.connect("activate", self.on_open_with, row)
                menu.append(open_with_item)

                menu.show_all()
                menu.popup_at_pointer(None)

    def on_open_with(self, menu_item, row):
        """Abrir un cuadro de diálogo para seleccionar una aplicación."""
        file_path = row[4]
        if file_path and os.path.exists(file_path):
            dialog = Gtk.AppChooserDialog.new_for_content_type("application/octet-stream", self)
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                app_info = dialog.get_app_info()
                app_info.launch_uris([Gio.File.new_for_path(file_path).get_uri()], None)
            dialog.destroy()

    def on_search(self, entry):
        """Filtrar el contenido del historial."""
        search_text = entry.get_text().lower()
        self.tree_store.clear()
        for item in self.clipboard_history:
            if search_text in item[0].lower():
                icon = self.get_icon("text-x-generic" if item[1] == "Texto" else "image-x-generic")
                self.tree_store.append([item[0][:50], item[1], item[2], icon, item[3] or ""])

    def on_clear_search(self, button):
        """Limpiar la barra de búsqueda."""
        self.search_entry.set_text("")
        self.on_search(self.search_entry)


def main():
    app = ClipboardManager()
    app.connect("destroy", Gtk.main_quit)
    app.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
