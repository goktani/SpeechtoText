import subprocess

def main():
    languages = {
        "1": ("Türkçe", "transcribe_tr.py"),
        "2": ("İngilizce", "transcribe_en.py"),
        "3": ("Fransızca", "transcribe_fr.py"),
        "4": ("İspanyolca", "transcribe_es.py")
    }

    print("Hangi dil için çalıştırmak istiyorsunuz?")
    for key, (language, _) in languages.items():
        print(f"{key}. {language}")

    choice = input("Lütfen bir seçim yapınız (1/2/3/4): ")

    if choice in languages:
        _, script = languages[choice]
        subprocess.run(["python", script])
    else:
        print("Geçersiz seçim! Lütfen 1, 2, 3 veya 4'ü seçiniz.")

if __name__ == "__main__":
    main()
