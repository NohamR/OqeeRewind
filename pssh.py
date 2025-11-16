from uuid import UUID
from pywidevine.pssh import PSSH


data = "AAAAiHBzc2gAAAAA7e+LqXnWSs6jyCfc1R0h7QAAAGgIARIQrKzUjhLvvbqkebbW2/EQtBIQWxKIsxtqP3iaIFYUu9f6xxIQXn4atxoopds39jbUXbiFVBIQUUJpv9uuzWKv4ccKTtooMRIQocf9FUFCoGm775zPIBr3HRoAKgAyADgASABQAA=="
pssh = PSSH(data)
pssh.set_key_ids([UUID("540103d1e13713f8ebdc90e468e6f97e"), UUID("acacd48e12efbdbaa479b6d6dbf110b4"), UUID("5b1288b31b6a3f789a205614bbd7fac7"), UUID("514269bfdbaecd62afe1c70a4eda2831"), UUID("a1c7fd154142a069bbef9ccf201af71d")])
print(pssh)