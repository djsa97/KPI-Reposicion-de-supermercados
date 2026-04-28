import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent


def run_step(script_rel_path: str):
    script_path = ROOT_DIR / script_rel_path
    print(f"Ejecutando {script_rel_path}...", flush=True)
    subprocess.run([sys.executable, str(script_path)], cwd=ROOT_DIR, check=True)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Actualiza el pipeline del dashboard de reposicion."
    )
    parser.add_argument(
        "--solo-base",
        action="store_true",
        help="Salta la extraccion del ERP y recompone solo consolidado, reposicion_base y control_dashboard.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    pasos = [
        "scripts/main_consolidado.py",
        "scripts/main_reposicion_base.py",
        "scripts/main_control_dashboard.py",
    ]

    if not args.solo_base:
        pasos = [
            "scripts/main_ventas.py",
            "scripts/main_notas_credito.py",
            "scripts/main_acuerdos.py",
            *pasos,
        ]
        faltantes_erp = [
            env_name for env_name in ("ERP_URL", "ERP_USER", "ERP_PASSWORD")
            if not os.getenv(env_name)
        ]
        if faltantes_erp:
            faltantes_txt = ", ".join(faltantes_erp)
            raise RuntimeError(
                f"Faltan variables de entorno del ERP: {faltantes_txt}. "
                "Configurarlas antes de ejecutar actualizar_reposicion.py."
            )

    for paso in pasos:
        run_step(paso)

    print("Actualización de reposición completada.", flush=True)


if __name__ == "__main__":
    main()
