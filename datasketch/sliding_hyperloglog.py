import os
import sys
from math import log2, log
from time import time
from hashlib import sha1
from BitVector import BitVector
import pyshark
import subprocess

##################################################################
"""
A LONG EXPLANATION OF HOW TO RUN THE PROGRAM IN LINE 200.
We start with global variables/constants:
"""

"""
The number of buckets, from which the first b bits is calculated.
"""

NUM_OF_BUCKETS = 1024
FIRST_B_BITS = int(log2(NUM_OF_BUCKETS))

"""
BIN_HASH_SIZE is the size in bits of the hashed element returned from the hash function.
BUCKET_SIZE is the size in bits of the buckets, which can represent a log(BIN_HASH_SIZE).
Pay attention! if your hash returns an int that cannot be represented in BIN_HASH_SIZE bits,
then an error will be thrown in hll_add_element function.
"""

BIN_HASH_SIZE = 32
BUCKET_SIZE = int(log2(BIN_HASH_SIZE))

# the time at the start of the execution, mainly used fof initializing the buckets.
START_TIME = time()

# the WINDOW of time we want to look at, in seconds
WINDOW = 500000

##################################################################
"""
Next we have complementary functions to help add elements and calculate them
"""

"""
a function which gets an element cid and returns its hashed value,
using sha1 as the hash function, and returning only the first BIN_HASH_SIZE bits.
"""


def get_element_hashed(cid):
    global BIN_HASH_SIZE
    hashed = sha1(str(cid).encode())
    digest = hashed.hexdigest()  # the hash value in hexa
    size = int(
        BIN_HASH_SIZE / 4)  # BIN_HASH_SIZE is in bits, but `digest` is in bytes, so BIN_HASH_SIZE bits are BIN_HASH_SIZE/4 bytes.
    digest_int = int(digest[:size], 16)
    return digest_int


"""
a function which remove the packets which are not relevant to the time t_value according to the constant WINDOW,
or if the packet's r_value=position of the leftmost 1-bit, is smaller than the r_value of the current packet.
finally it adds the current packet to the lfpm list.
@reg_index- the bucket we want to update
@t_value- the time when the current packet has arrived
@r_value- the position of the leftmost 1-bit of the current packet
"""


def update_lfpm(reg_index, t_value, r_value):
    global regs, WINDOW, BUCKET_SIZE
    regs[reg_index][:] = [r for r in regs[reg_index] if not (t_value - WINDOW > r[0] or r[1].intValue() < r_value)]
    regs[reg_index].append((t_value, BitVector(intVal=r_value, size=BUCKET_SIZE)))


"""
a function which finds out the leftmost 1-bit, denoted also as rho.
@w- the (hashed) number we want to find the position of the leftmost 1-bit.
@max_width- the maximum binary size of w.
"""


def get_rho(w, max_width):
    rho = max_width - w.bit_length() + 1
    return rho


"""
a function which calculte the alpha constant thanks to well known values according to the number of buckets.
"""


def get_alpha_constant():
    global NUM_OF_BUCKETS
    if NUM_OF_BUCKETS <= 16:
        return 0.673
    elif NUM_OF_BUCKETS == 32:
        return 0.679
    elif NUM_OF_BUCKETS == 64:
        return 0.709
    else:
        return 0.7213 / (1 + (1.079 / NUM_OF_BUCKETS))


"""
a function which finds out if a bucket is empty- the r value is either 0 or empty.
@reg_index- the specific bucket we want to check.
"""


def bucket_is_empty(reg_index):
    global regs
    for r in regs[reg_index]:
        if r[1].intValue() != 0:
            return False
    return True


"""
a function for testing mode, which adds the cid at a time to the list
counter which holds all the unique cids.
@time- arrival time of the cid.
@cid- the cid of the packet.
@counter- the list which holds all the unique cds
"""


def counter_add(time, cid, counter):
    counter[:] = [r for r in counter if not (cid == r[1])]
    counter.append((time, cid))


"""
a function for testing mode, which updates the list of unique cids to hold
only the cids which are relevant to the current window of time, called right
before printing the real cardinality to this window of time.
@time- finish time.
@counter- the list which holds all the unique cids
"""


def update_counter(finish_time):
    global WINDOW, counter
    counter[:] = [c for c in counter if not (finish_time - WINDOW > c[0])]


##################################################################

##################################################################
"""
the hll functions: the add function and the count function:
"""

"""
a function which adds an element cid that arrived at time t_value
it first hash it, then parse the first b bits and the rest c bits,
and finally update the lpfm list and the cid at time t_value.
x = hash(cid)
x = x_1 x_2...x_b x_b+1...x_n
    ------b------ -----c-----
"""


def hll_add_element(t_value, cid):
    global NUM_OF_BUCKETS, FIRST_B_BITS, BUCKET_SIZE, regs, BIN_HASH_SIZE, make_string

    # first step- hashing the cid
    hashed_cid = get_element_hashed(cid)

    # second step- finding the suitable bucket through the first b bits
    reg_index = hashed_cid & (NUM_OF_BUCKETS - 1)

    # third step- finding the leftmost bit in the rest of the hashed_cid_binary
    w = hashed_cid >> FIRST_B_BITS
    leftmost_bit = get_rho(w, BIN_HASH_SIZE - FIRST_B_BITS)

    # final step- update the lfpm of the bucket to have only relevant packets
    # and save the pos of the biggest leftmost bit in the suitable bucket
    update_lfpm(reg_index, t_value, leftmost_bit)


"""
a function which count the estimated cardinality in the last WINDOW time,
according to the finish_time time.
"""


def hll_count_cardinality(finish_time):
    global regs, NUM_OF_BUCKETS

    alpha = get_alpha_constant()  # find the constant alpha for the calculations later
    tmp_max_regs = []  # a list which will hold only the largest r_value(position of the leftmost 1-bit) of each bucket.
    current_time = finish_time  # to know the current time so we could update the lfpm lists.
    empty_buckets = 0  # a variable which will count the amount of empty buckets.

    # update all of the lfpm to only have the packets which are relevant to the WINDON of time.
    # and then update the temporary list tmp_max_regs.
    # in addition, count the number of empty buckets.
    for x in range(NUM_OF_BUCKETS):
        update_lfpm(x, current_time, 0)
        if bucket_is_empty(x):
            empty_buckets += 1
        """
        1. max(regs[x],key=lambda item:item[1] = find the largest r_value in the lfpm list, returns a *tuple*.
        2. max(regs[x],key=lambda item:item[1)[1] = return the second value of the tuple==the bitvector representing the r_value
        3. max(regs[x],key=lambda item:item[1])[1].intValue() = return the integer value of the bitvector representing the r_value.
        4. append = add this r_value calculated above to the temporary list of maximum r_values.
        """
        tmp_max_regs.append(max(regs[x], key=lambda item: item[1])[1].intValue())
    harmonic_mean = sum([pow(2, -x) for x in tmp_max_regs])  # calculate the harmonic mean
    harmonic_mean = 1 / harmonic_mean
    m_power2 = NUM_OF_BUCKETS ** 2
    cardinality = alpha * m_power2 * harmonic_mean
    if cardinality <= 5 * NUM_OF_BUCKETS:  # range correction
        if empty_buckets != 0:
            cardinality = NUM_OF_BUCKETS * log(NUM_OF_BUCKETS / empty_buckets)
    return cardinality


##########################################################

"""
changing the parameters:
first we check if the user even wants to change them, if not- use the parameters which
appears in the start of this file.
there are 3 main parameters you can change-
1. the size of the hash outcome- recommended to be 32 or 64, according to the papers. MUST BE A POWER OF 2.
2. the number of buckets. MUST BE A POWER OF 2.
3. size of the window(in seconds).
4. if we are in testing mode or not(y for testing, empty for not).

to run this file with the changes, run:
python sliding_hll.py <size_of_hash_outcome> <number_of_buckets> <size_of_window>
for example: python sliding_hll.py 32 1024 1- meaning a hash outcome of 32bits, 1024 buckets,
1 second of a window and not a testing.
"""

testing_mode = False
if len(sys.argv) > 1:
    BIN_HASH_SIZE = int(sys.argv[1])
    BUCKET_SIZE = int(log2(BIN_HASH_SIZE))
    NUM_OF_BUCKETS = int(sys.argv[2])
    FIRST_B_BITS = int(log2(NUM_OF_BUCKETS))
    WINDOW = int(sys.argv[3])
    if len(sys.argv) == 5:
        if sys.argv[4] == 'y':
            testing_mode = True

# we start with initializing all the registers to an empty lpfm list.
regs = []
for x in range(NUM_OF_BUCKETS):
    regs.append([])  # each register has a lfpm list
    regs[x].append(
        (START_TIME, BitVector(intVal=0, size=BUCKET_SIZE)))  # for each register, start with lfpm of (START_TIME, 0)

# TO TEST THE SCRIPT
# initialize a list that will count the real cardinality
counter = []

"""
starting to catch QUIC packets and adding them up until Ctrl+C interruption is happening
"""

print("~~~adding phase~~~")
live_cap = pyshark.LiveCapture(interface="\Device\\NPF_{D11C2819-F8D1-43D0-A08E-258A26BB3132}", include_raw=True, use_json=True)
emptySet = set()
try:
    for packet in live_cap.sniff_continuously(packet_count=10000):
        for layer in packet.layers:
            if layer.layer_name == 'ip':
                if layer.has_field('src_host'):  # extract the dcid (Destination Connection ID)
                    cid = layer.get_field('src_host')
                    arrival_time = time()
                    hll_add_element(arrival_time, str(cid))
                    emptySet.add(cid)
                    if testing_mode:
                        counter_add(arrival_time, cid, counter)
except KeyboardInterrupt:  # when stopped with Ctrl+C
    print("~~~finished adding~~~")
    print("~~~counting phase~~~")
    finished_time = time()
    x = hll_count_cardinality(finished_time)
    if testing_mode:
        update_counter(finished_time)
    print("~~~finished couting~~~")
    print("~~~the estimated cardinality is:~~~")
    print(x)
    if testing_mode:
        print("~~~the real cardinality is:~~~")
        print(len(counter))
except EOFError:
    pass
finally:
    print("~~~byebye!~~~")

finished_time = time()
x = hll_count_cardinality(finished_time)
if testing_mode:
    update_counter(finished_time)
print("~~~finished couting~~~")
print("~~~the estimated cardinality is:~~~")
print(x)
print("~~~the real cardinality is:~~~")
print(len(emptySet))
if testing_mode:
    print("~~~the real cardinality is:~~~")
    print(len(counter))