# geigermon

## example usage

### single machine

```
  ./geigermon -s gmc300eplus /dev/ttyUSB0 -S stdout
```

### two machines

(e.g. server and workstation)

```
  ./geigermon -s gmc300eplus /dev/ttyUSB0 -S multicast 1.2.3.4 224.0.0.5 1111 1  
```

```
  ./geigermon -s multicast 1.2.3.5 224.0.0.5 1111 1.2.3.4 -S file /run/user/1111/geigermon.json
```
