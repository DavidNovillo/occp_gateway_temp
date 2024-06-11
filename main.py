import subprocess


def main():
    subprocess.call(["git", "pull", "origin", "main"],
                    cwd='/home/pi/OCPP/ocpp_gateway')
    try:
        subprocess.call(["python", "programa_principal.py"],
                        cwd='/home/pi/OCPP/ocpp_gateway')
    except:
        print("Programa terminado")


if __name__ == "__main__":
    main()
