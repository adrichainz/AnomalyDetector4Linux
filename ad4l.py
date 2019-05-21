#!/usr/bin/python3
import statistics
import subprocess
import threading
import psutil
import json
import time

############################# IDEAS ###################################################
# dict de procesos 
# historico cpu, mem, io
# historico de net
# alerta cuando algo cambia drásticamente sin sentido notify-send "hola cara bola"
#######################################################################################

### Historial de dispositivos conectados
# 1. Si se quiere inicializar con lista vacía para detectar nuevos en la primera iteración
# dispositivos_conectados = []

# 2. Si se quiere inicializar con el estado actual de dispositivos
df = subprocess.run(['lsusb'], stdout=subprocess.PIPE)
dispositivos_conectados = df.stdout.split(b"\n")

### Historial de procesos
procesos = {}
for proc in psutil.process_iter():
    procesos[proc.pid] = {
    "name": proc.name(),
    "cpu": [proc.cpu_percent()],
    "mem": [proc.memory_full_info().vms], 
    "ior": [proc.io_counters().read_bytes], 
    "iow": [proc.io_counters().write_bytes]
    }

### Historial de red
red = {}
red["bytes_sent"] = [psutil.net_io_counters().bytes_sent]
red["bytes_recv"] = [psutil.net_io_counters().bytes_recv]

#######################################################################################

# Función encargada de detectar los recursos utilizados por cada proceso (memoria, CPU, etc.)
# def listarProcesos():
#     procesos = {}
#     cabeceras = ["pid", "user", "pr", "ni", "virt", "res", "shr", "s" "cpu", "mem", "time"]
#     top = subprocess.run(['top', '-n 1', '-b'], stdout=subprocess.PIPE)
#     lineas = top.stdout.split(b"\n")
#     for linea in lineas[7:]:
#         campos = linea.split()
#         if len(campos) == 12:
#             campos = list(map(lambda x: x.decode('ascii'), campos))
#             valor = [[c] for c in campos[0:10]]
#             dicValor = dict(zip(cabeceras, valor))
#             if campos[11] not in procesos:
#                 procesos[campos[11]] = dicValor
#             else:
#                 for c in cabeceras:
#                     procesos[campos[11]][c] = procesos[campos[11]][c] + dicValor[c]
#             # print(procesos)
#             # exit()
#     return procesos

#######################################################################################

# Función encargada de detectar anomalías en el uso de un recurso por parte de un proceso
def detectarAnomalias():
    global procesos
    for proc in psutil.process_iter():
        procesos[proc.pid]["cpu"] += [proc.cpu_percent()]
        procesos[proc.pid]["mem"] += [proc.memory_full_info().vms]
        procesos[proc.pid]["ior"] += [proc.io_counters().read_bytes]
        procesos[proc.pid]["iow"] += [proc.io_counters().write_bytes]
        procesos[proc.pid]["cpu"] = procesos[proc.pid]["cpu"][-5:]
        procesos[proc.pid]["mem"] = procesos[proc.pid]["mem"][-5:]
        procesos[proc.pid]["ior"] = procesos[proc.pid]["ior"][-5:]
        procesos[proc.pid]["iow"] = procesos[proc.pid]["iow"][-5:]

    for key in procesos:
        print(statistics.variance(procesos[key]["cpu"]))
        print(statistics.variance(procesos[key]["mem"]))
        print(statistics.variance(procesos[key]["ior"]))
        print(statistics.variance(procesos[key]["iow"]))
        # si alguno de esos prints es > que 40, alert  key es el pid y el nombre es procesos[key]["name"]

#######################################################################################

# Función encargada de detectar anomalías en el uso de la red
def detectarRed():
    global red
    red["bytes_sent"] += [psutil.net_io_counters().bytes_sent]
    red["bytes_recv"] += [psutil.net_io_counters().bytes_recv]
    red["bytes_sent"] = red["bytes_sent"][-5:]
    red["bytes_recv"] = red["bytes_recv"][-5:]

#######################################################################################

# Función encargada de detectar cuándo se ha conectado un nuevo dispositivo USB
def listarDispositivos():
    # print("Comprobando lista de dispositivos conectados...")
    df = subprocess.run(['lsusb'], stdout=subprocess.PIPE)
    dispositivos_actuales = df.stdout.split(b"\n")
    
    global dispositivos_conectados
    if(dispositivos_actuales > dispositivos_conectados):
        print(" - ¡Un nuevo dispositivo ha sido conectado al sistema!")
    elif(dispositivos_actuales < dispositivos_conectados):
        print(" - ¡Un dispositivo ha sido desconectado del sistema!")

    dispositivos_conectados = dispositivos_actuales

########################################################################################

# Función encargada de comprobar si existe algún usuario sin contraseña
def comprobarUsuariosSinPassword():
    df = subprocess.run(['sudo awk -F: \'($2 == "") {print}\' /etc/shadow'], stdout=subprocess.PIPE)
    if(len(df.stdout) > 0):
        print(" - ¡Se ha encontrado un usuario sin contraseña registrado en el sistema!")
        subprocess.run(['notify-send -u critical "Problema de seguridad" "¡Encontrado un usuario sin contraseña en el sistema!"'],
            stdout=subprocess.PIPE)

########################################################################################

# Función encargada de comprobar si el usuario root acepta login vía SSH
def comprobarPasswordRootSsh():
    subprocess.run(['grep "PermitRootLogin " /etc/ssh/sshd_config 2>/dev/null | grep -v "#" | awk \'{print  $2}\''],
        stdout=subprocess.PIPE)
    if(len(df.stdout) > 0):
        print(" - ¡El usuario root está aceptando conexiones a través de SSH!")
        subprocess.run(['notify-send -u critical "Problema de seguridad" "¡El usuario root acepta conexiones entrantes por SSH!"'],
            stdout=subprocess.PIPE)

########################################################################################

### Ejecución del script en segundo plano
while(True):
    listarProcesos()
    detectarAnomalias()
    listarDispositivos()
    comprobarUsuariosSinPassword()
    comprobarPasswordRootSsh()
    time.sleep(3)
