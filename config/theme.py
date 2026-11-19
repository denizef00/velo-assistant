# theme.py
# Velo UI Renk ve Stil Konfigürasyonu

THEME_CONFIG = {
    "appearance_mode": "dark",      # "dark" veya "light"
    "color_theme": "dark-blue",      # Varsayılan customtkinter teması
    
    # Arka Plan Renkleri
    "bg_dark": "#0F111A",           # Ana pencere arka planı
    "card_bg": "#1A1D2A",           # Terminal ve panel arka planı
    
    # Mod Buton Renkleri (Normal, Hover)
    "buttons": {
        "game": {
            "fg": "#7289DA",        # Oyun Modu Buton Rengi (Mavi/Mor tonu)
            "hover": "#5B6EAE",
            "text": "#FFFFFF"
        },
        "desktop": {
            "fg": "#00A86B",     # Masaüstü Modu Buton Rengi (Yeşil tonu)
            "hover": "#008554",
            "text": "#FFFFFF"
        },
        "test": {
            "fg": "#E5A93C",        # Test Modu Buton Rengi (Sarı/Turuncu tonu)
            "hover": "#B8862E",
            "text": "#FFFFFF"
        }
    },
    
    # Mini Terminal Renkleri
    "terminal": {
        "bg": "#090A0F",            # Terminal içi koyu arka plan
        "text": "#00FF66",          # Terminal çıktı metin rengi (Hacker/Cyber neon yeşil)
        "prompt_symbol": "Velo> ", # Terminal başlangıç simgesi
        "input_bg": "#141722",      # Metin giriş kutusu arka planı
        "border_color": "#2A2E3D"
    },
    
    # Font Yapılandırması
    "fonts": {
        "title": ("Consolas", 14, "bold"),
        "button": ("Segoe UI", 12, "bold"),
        "terminal": ("Consolas", 12)  # Sabit genişlikli kod fontu
    }
}