import os
import sys

def main():
    """Run administrative tasks."""
    # Garante que aponta para a subpasta AgencyOS onde estará o settings.py
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AgencyOS.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Django não encontrado.") from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()