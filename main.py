import subprocess


def main():
    subprocess.call(["git", "pull", "origin", "main"],
                    cwd='/home/pi/OCPP_TEMP/occp_gateway_temp')
    try:
        subprocess.call(["python3.11", "programa_principal.py"],
                        cwd='/home/pi/OCPP_TEMP/occp_gateway_temp')
    except:
        print("Programa terminado")


if __name__ == "__main__":
    main()
