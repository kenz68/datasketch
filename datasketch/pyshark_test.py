import pyshark

capture = pyshark.LiveCapture("\Device\\NPF_{D11C2819-F8D1-43D0-A08E-258A26BB3132}")
capture.sniff(timeout=2)
print(capture)

live_cap = pyshark.LiveCapture(interface="\Device\\NPF_{D11C2819-F8D1-43D0-A08E-258A26BB3132}", include_raw=True, use_json=True)
try:
    for packet in live_cap.sniff_continuously():
        for layer in packet.layers:
            if layer.layer_name == 'ip':
                if layer.has_field('host'):  # extract the dcid (Destination Connection ID)
                    cid = layer.get_field('host')
                    print(cid)
except KeyboardInterrupt:  # when stopped with Ctrl+C
    print("~~~finished adding~~~")
    print("~~~counting phase~~~")
    print("~~~finished couting~~~")
    print("~~~the estimated cardinality is:~~~")
except EOFError:
    pass
finally:
    print("~~~byebye!~~~")