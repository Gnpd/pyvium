# PYVIUM

[English](./README.md) | [中文](./README.zh.md) | Español

Wrapper de Python para la DLL del driver de IviumSoft, que permite controlar potenciostatos Ivium y procesar datos experimentales directamente desde Python.

PYVIUM ofrece:

- Acceso directo a las funciones Core originales de IviumSoft
- Una interfaz Pythonica de alto nivel con manejo de excepciones y utilidades extendidas

---

## Características

- Acceso completo a las funciones de la DLL del driver de IviumSoft
- Interfaz amigable para Python
- Gestión de excepciones
- Herramientas de procesamiento de datos
- Utilidades de conversión por lotes
- Sincronización en modo batch

---

## Requisitos

PYVIUM requiere que IviumSoft esté instalado en una máquina Windows, ya que utiliza la DLL oficial del driver.

Descarga IviumSoft aquí:

https://www.ivium.com/support/#Software%20update

Esta versión de PYVIUM incluye la DLL de la versión **4.1239** de IviumSoft.

---

## Instalación

Instala PYVIUM fácilmente con pip:

```
pip install pyvium
```

O con poetry:

```
poetry add pyvium
```

## Inicio rápido

### Usando las funciones Core (acceso directo a la DLL)

Para usar las mismas funciones disponibles en la «DLL del driver de IviumSoft», importa la clase Core de la siguiente manera. Todas las funciones devuelven un código de resultado (entero) y un valor de retorno cuando está disponible. Para más información consulta la documentación de IviumSoft.

```
from pyvium import Core

Core.IV_open()
Core.IV_getdevicestatus()
Core.IV_close()
```

## Usando la interfaz de alto nivel de Pyvium (recomendado)

Es un wrapper sobre las funciones Core que añade:

- Gestión de excepciones (puedes ver un ejemplo [aquí](https://github.com/Gnpd/pyvium/blob/main/docs/error_management.md))
- Sintaxis más limpia
- Funcionalidad adicional

```
from pyvium import Pyvium

Pyvium.open_driver()
Pyvium.get_device_status()
Pyvium.close_driver()
```

## Herramientas de procesamiento de datos

Ofrece funcionalidad adicional para el procesamiento de datos:

```
from pyvium import Tools

Tools.convert_idf_dir_to_csv()
```

## Ejemplos y notebooks

Una serie de Jupyter notebooks cubre la API completa:

| Notebook | Tema |
|---|---|
| `01_getting_started` | Instalación, ciclo de vida del driver, manejo de errores |
| `02_device_and_instance_management` | Conectar dispositivos, cambiar instancias |
| `03_direct_mode_basics` | Control de potencial/corriente, encendido/apagado de celda |
| `04_direct_mode_signals` | DAC/ADC, E/S digital, señal AC |
| `05_bipotentiostat_and_we32` | BiStat WE2 y array WE32 de 32 canales |
| `06_method_mode` | Cargar, ejecutar, monitorear y guardar experimentos |
| `07_data_processing` | Parsear archivos IDF, exportar a CSV (sin hardware) |
| `08_batch_and_synchronization` | Setpoints multi-dispositivo y ejecución en paralelo |
| `09_trigger_reference` | Mecanismos de trigger entre Python e IviumSoft |

Los notebooks en español se encuentran en el directorio [`notebooks/es/`](https://github.com/Gnpd/pyvium/tree/main/notebooks/es).

## Funciones implementadas

La lista de funciones implementadas está disponible [aquí](https://github.com/Gnpd/pyvium/blob/main/docs/method_list.md).

## Soporte y consultoría

Si necesitas ayuda para integrar PYVIUM en tu aplicación, conectar instrumentos Ivium o desarrollar flujos de trabajo personalizados, hay disponible un servicio de consultoría profesional.

Contacto:

📧 a.gutierrez@g-npd.com

También puedes apoyar el proyecto a través de GitHub Sponsors:

https://github.com/sponsors/Gnpd

Los patrocinadores reciben soporte prioritario y contribuyen al desarrollo futuro del proyecto.

## Enlaces

- [Ver en GitHub](https://github.com/Gnpd/pyvium)
- [Ver en PyPI](https://pypi.org/project/pyvium)
