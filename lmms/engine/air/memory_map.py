import os
import mmap
import struct
from typing import Dict, List, Tuple, Optional

class GGUFMemoryMap:
    """
    Zero-latency virtual memory mapping for GGUF model files.
    Enables layer-by-layer sequential slicing and direct kernel readahead/eviction
    (posix_fadvise) to eliminate Linux page-cache thrashing during Regime 3 streaming.
    """
    def __init__(self, filepath: str):
        self.filepath = os.path.abspath(filepath)
        self.file_size = os.path.getsize(self.filepath)
        self._fd = os.open(self.filepath, os.O_RDONLY)
        self._mmap = mmap.mmap(self._fd, 0, access=mmap.ACCESS_READ)
        
        self.layer_offsets: Dict[int, Tuple[int, int]] = {} # layer_idx -> (start_byte, total_bytes)
        self.tensor_info: Dict[str, Dict[str, Any]] = {}
        self._parse_tensor_index()

    def _parse_tensor_index(self):
        """Parse tensor offsets to group weights by layer index."""
        try:
            # Quick parse of tensor metadata from header
            self._mmap.seek(0)
            magic = self._mmap.read(4)
            if magic != b'GGUF':
                return
                
            version, tensor_count, kv_count = struct.unpack('<IQQ', self._mmap.read(20))
            
            def read_str():
                l = struct.unpack('<Q', self._mmap.read(8))[0]
                return self._mmap.read(l).decode('utf-8', errors='ignore')

            # Skip KV pairs to reach tensor info
            fixed_sizes = {0: 1, 1: 1, 7: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 4, 10: 8, 11: 8, 12: 8}
            for _ in range(kv_count):
                key = read_str()
                val_type = struct.unpack('<I', self._mmap.read(4))[0]
                if val_type in fixed_sizes:
                    self._mmap.seek(fixed_sizes[val_type], os.SEEK_CUR)
                elif val_type == 8:
                    s_len = struct.unpack('<Q', self._mmap.read(8))[0]
                    self._mmap.seek(s_len, os.SEEK_CUR)
                elif val_type == 9:
                    arr_type, arr_len = struct.unpack('<IQ', self._mmap.read(12))
                    if arr_type in fixed_sizes:
                        self._mmap.seek(arr_len * fixed_sizes[arr_type], os.SEEK_CUR)
                    elif arr_type == 8:
                        for _ in range(arr_len):
                            s_len = struct.unpack('<Q', self._mmap.read(8))[0]
                            self._mmap.seek(s_len, os.SEEK_CUR)

            # Record starting position of tensor info
            tensor_infos = []
            for _ in range(tensor_count):
                t_name = read_str()
                n_dims = struct.unpack('<I', self._mmap.read(4))[0]
                dims = [struct.unpack('<Q', self._mmap.read(8))[0] for _ in range(n_dims)]
                t_type = struct.unpack('<I', self._mmap.read(4))[0]
                t_offset = struct.unpack('<Q', self._mmap.read(8))[0]
                tensor_infos.append((t_name, t_offset, dims, t_type))

            # Alignment padding to data start
            alignment = 32
            curr_pos = self._mmap.tell()
            data_start = (curr_pos + (alignment - 1)) & ~(alignment - 1)

            # Group by layer
            layer_bounds: Dict[int, List[int]] = {}
            for name, rel_offset, dims, t_type in tensor_infos:
                abs_offset = data_start + rel_offset
                # Calculate size approx from dims
                elements = 1
                for d in dims: elements *= d
                # Most quant tensors are ~0.5 - 1.0 byte/element
                est_bytes = max(32, int(elements * 0.56)) 
                
                # Check if layer tensor (e.g. blk.0., layers.0.)
                parts = name.split('.')
                for i, p in enumerate(parts):
                    if (p in ('blk', 'layers', 'layer') and i + 1 < len(parts) and parts[i+1].isdigit()):
                        l_idx = int(parts[i+1])
                        if l_idx not in layer_bounds:
                            layer_bounds[l_idx] = [abs_offset, abs_offset + est_bytes]
                        else:
                            layer_bounds[l_idx][0] = min(layer_bounds[l_idx][0], abs_offset)
                            layer_bounds[l_idx][1] = max(layer_bounds[l_idx][1], abs_offset + est_bytes)
                        break

            for l_idx, (start, end) in layer_bounds.items():
                self.layer_offsets[l_idx] = (start, end - start)
                
        except Exception as e:
            # Fallback uniform division if header had non-standard alignment
            pass

    def get_layer_slice(self, layer_idx: int, total_layers: int = 36) -> Tuple[int, int]:
        """Returns (start_offset, length_bytes) for the specified layer."""
        if layer_idx in self.layer_offsets:
            return self.layer_offsets[layer_idx]
        # Uniform block estimation fallback
        layer_size = self.file_size // max(total_layers, 1)
        start = layer_idx * layer_size
        return (start, layer_size)

    def prefetch_layer(self, layer_idx: int, total_layers: int = 36):
        """Asynchronously trigger OS readahead for the upcoming layer."""
        try:
            offset, length = self.get_layer_slice(layer_idx, total_layers)
            if hasattr(os, 'posix_fadvise'):
                os.posix_fadvise(self._fd, offset, length, os.POSIX_FADV_WILLNEED)
        except Exception:
            pass

    def evict_layer(self, layer_idx: int, total_layers: int = 36):
        """Immediately discard passed layer pages from Linux page cache to avoid OS freezes."""
        try:
            offset, length = self.get_layer_slice(layer_idx, total_layers)
            if hasattr(os, 'posix_fadvise'):
                os.posix_fadvise(self._fd, offset, length, os.POSIX_FADV_DONTNEED)
        except Exception:
            pass

    def close(self):
        try:
            if self._mmap:
                self._mmap.close()
            if self._fd:
                os.close(self._fd)
        except Exception:
            pass
