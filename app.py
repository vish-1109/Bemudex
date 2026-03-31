import customtkinter as ctk
from ui import App

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

if __name__ == "__main__":
    root = ctk.CTk()
    app = App(root)
    root.mainloop()