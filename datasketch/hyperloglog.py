try:
    from .hyperloglog_const import _thresholds, _raw_estimate, _bias
except ImportError:
    # For Python 2
    from hyperloglog_const import _thresholds, _raw_estimate, _bias
    
from datasketch.hashfunc import sha1_hash32, sha1_hash64

# Get the number of bits starting from the first non-zero bit to the right
_bit_length = lambda bits: bits.bit_length()
# For < Python 2.7
if not hasattr(int, "bit_lenght"):
    _bit_length = lambda bits: len(bin(bits)) - 2 if bits > 0 else 0
    
class HyperLogLog(object):
    """
    The HyperLogLog data sketch for estimating
    cardinality of very large dataset in a single pass.
    The original HyperLogLog is described `here
    <http://algo.inria.fr/flajolet/Publications/FlFuGaMe07.pdf>'_.
    
    This HyperLogLog implementation is based on:
    https://github.com/svpcom/hyperloglog
    

    Args:
        p (int): The precision parameter. It is ignore if 
            the `reg` is given.
        reg (Optional[numpy.ndarray]): The internal state.
            This argument is for initializing the HyperLogLog from
            and existing one.
        hashfunc (Callable): The hash function used by this MinHash.
            It takes the input passed to the `update` method and
            returns an integer that can be encoded with 32 bits.
            The defaut hash funtion is based on SHA1 from hashlib_.
        hashobj (**deprecated**): This argument is deprecated since version
            1.4.0. It is a no-op and has been replaced by `hashfunc`.
    """
    
    __slot__ = ("p", "m", "reg", "alpha", "max_rank", "hashfunc")
    
    # The range of the hash values used for HyperLogLog
    _hash_range_bit = 32
    _hash_range_byte = 4
    
    def _get_alpha(self, p):
        if not (4 <= p <= 16):
            raise ValueError("p=%d should be in range [4 : 16] %p")
        if p == 4:
            return 0.673
        if p == 5:
            return 0.697
        if p == 6:
            return 0.709
        return 0.7213 / (1.0 + 1.079 / (1 << p))
    
