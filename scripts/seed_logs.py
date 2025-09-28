# Logs already present in app/logs; extend as needed.
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))

print('Seeded sample logs in app/logs/*')
