import subprocess
import sys
import os

def run_suite(iteration):
    print(f"\n{'='*20}")
    print(f" EJECUCIÓN #{iteration}")
    print(f"{'='*20}\n")
    
    # Ejecutar behave apuntando a la carpeta de features
    # Usamos shell=True en Windows para mayor compatibilidad con comandos
    result = subprocess.run(["behave"], cwd=".", capture_output=False)
    return result.returncode

def main():
    # Asegurarse de que estamos en el directorio correcto
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    success_count = 0
    total_runs = 3
    
    for i in range(1, total_runs + 1):
        if run_suite(i) == 0:
            success_count += 1
        else:
            print(f"\n❌ Error en la ejecución #{i}")
    
    print(f"\n{'='*40}")
    print(f" RESUMEN DE CONSISTENCIA: {success_count}/{total_runs} éxitos")
    print(f"{'='*40}")
    
    if success_count == total_runs:
        print("\n✅ Suite estable y consistente.")
        sys.exit(0)
    else:
        print("\n⚠️ Se detectaron fallos intermitentes o errores permanentes.")
        sys.exit(1)

if __name__ == "__main__":
    main()
