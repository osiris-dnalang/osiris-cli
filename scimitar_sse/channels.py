"""
Scimitar-SSE Communication Channels
Cross-Device Phase Synchronization via BT/WiFi/RF

Channels:
- Bluetooth LE (2.4GHz)
- WiFi 2.4GHz / 5GHz
- RF 433MHz / 915MHz
"""

import time
import struct
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
import threading
import queue

# Physical Constants
LAMBDA_PHI = 2.176435e-8
THETA_LOCK = 51.843


@dataclass
class PhasePacket:
    """Phase synchronization packet for cross-device communication"""
    sequence_id: int
    timestamp: float
    group_a_phase: float
    group_b_phase: float
    theta_lock: float
    coherence: float
    decoherence: float
    device_id: str
    checksum: str = ""

    def __post_init__(self):
        if not self.checksum:
            self.checksum = self._compute_checksum()

    def _compute_checksum(self) -> str:
        """Compute SHA256 checksum of packet data"""
        data = f"{self.sequence_id}:{self.timestamp}:{self.group_a_phase}:{self.group_b_phase}:{self.theta_lock}:{self.coherence}:{self.device_id}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def validate(self) -> bool:
        """Validate packet checksum"""
        return self.checksum == self._compute_checksum()

    def to_bytes(self) -> bytes:
        """Serialize packet to bytes for transmission"""
        # Header: 4 bytes magic, 4 bytes sequence
        header = struct.pack(">4sI", b"SCIM", self.sequence_id)

        # Payload: 6 doubles + device_id + checksum
        payload = struct.pack(
            ">6d",
            self.timestamp,
            self.group_a_phase,
            self.group_b_phase,
            self.theta_lock,
            self.coherence,
            self.decoherence
        )

        # Device ID (32 bytes, null-padded)
        device_bytes = self.device_id.encode()[:32].ljust(32, b'\x00')

        # Checksum (16 bytes)
        checksum_bytes = self.checksum.encode()[:16].ljust(16, b'\x00')

        return header + payload + device_bytes + checksum_bytes

    @classmethod
    def from_bytes(cls, data: bytes) -> 'PhasePacket':
        """Deserialize packet from bytes"""
        # Parse header
        magic, sequence_id = struct.unpack(">4sI", data[:8])
        if magic != b"SCIM":
            raise ValueError("Invalid packet magic")

        # Parse payload
        (timestamp, group_a_phase, group_b_phase,
         theta_lock, coherence, decoherence) = struct.unpack(">6d", data[8:56])

        # Parse device ID and checksum
        device_id = data[56:88].rstrip(b'\x00').decode()
        checksum = data[88:104].rstrip(b'\x00').decode()

        return cls(
            sequence_id=sequence_id,
            timestamp=timestamp,
            group_a_phase=group_a_phase,
            group_b_phase=group_b_phase,
            theta_lock=theta_lock,
            coherence=coherence,
            decoherence=decoherence,
            device_id=device_id,
            checksum=checksum
        )


class PhaseChannel(ABC):
    """Abstract base class for phase synchronization channels"""

    def __init__(self, device_id: str):
        self.device_id = device_id
        self.sequence_counter = 0
        self.connected = False
        self.rx_queue: queue.Queue = queue.Queue()
        self.tx_queue: queue.Queue = queue.Queue()
        self.stats = {
            "packets_sent": 0,
            "packets_received": 0,
            "errors": 0,
            "last_rssi": 0
        }

    @abstractmethod
    def connect(self) -> bool:
        """Establish channel connection"""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close channel connection"""
        pass

    @abstractmethod
    def transmit(self, packet: PhasePacket) -> bool:
        """Transmit a phase packet"""
        pass

    @abstractmethod
    def receive(self, timeout: float = 1.0) -> Optional[PhasePacket]:
        """Receive a phase packet"""
        pass

    def create_packet(self, group_a_phase: float, group_b_phase: float,
                      coherence: float, decoherence: float) -> PhasePacket:
        """Create a new phase packet"""
        self.sequence_counter += 1
        return PhasePacket(
            sequence_id=self.sequence_counter,
            timestamp=time.time(),
            group_a_phase=group_a_phase,
            group_b_phase=group_b_phase,
            theta_lock=THETA_LOCK,
            coherence=coherence,
            decoherence=decoherence,
            device_id=self.device_id
        )

    def get_stats(self) -> Dict:
        """Get channel statistics"""
        return self.stats.copy()


class BluetoothLEChannel(PhaseChannel):
    """
    Bluetooth LE (2.4GHz) phase synchronization channel.
    Uses GATT characteristics for phase data exchange.
    """

    def __init__(self, device_id: str, service_uuid: str = "00001234-0000-1000-8000-00805f9b34fb"):
        super().__init__(device_id)
        self.frequency = "2.4GHz"
        self.service_uuid = service_uuid
        self.characteristic_uuid = "00005678-0000-1000-8000-00805f9b34fb"

        # Simulated BT adapter state
        self._adapter_ready = False
        self._peers: List[str] = []

    def connect(self) -> bool:
        """Initialize BT LE adapter and start advertising/scanning"""
        try:
            # In real implementation, this would use bluepy/bleak
            self._adapter_ready = True
            self.connected = True
            print(f"[BT LE] Adapter initialized on {self.frequency}")
            return True
        except Exception as e:
            print(f"[BT LE] Connection failed: {e}")
            self.stats["errors"] += 1
            return False

    def disconnect(self) -> None:
        """Stop BT LE and close adapter"""
        self._adapter_ready = False
        self.connected = False
        self._peers.clear()
        print("[BT LE] Adapter closed")

    def transmit(self, packet: PhasePacket) -> bool:
        """Transmit phase packet via BT LE characteristic"""
        if not self.connected:
            return False

        try:
            data = packet.to_bytes()
            # In real implementation, this would write to GATT characteristic
            # For simulation, we just track stats
            self.stats["packets_sent"] += 1
            self.tx_queue.put(packet)
            return True
        except Exception as e:
            print(f"[BT LE] Transmit error: {e}")
            self.stats["errors"] += 1
            return False

    def receive(self, timeout: float = 1.0) -> Optional[PhasePacket]:
        """Receive phase packet from BT LE characteristic"""
        if not self.connected:
            return None

        try:
            packet = self.rx_queue.get(timeout=timeout)
            if packet.validate():
                self.stats["packets_received"] += 1
                return packet
            else:
                self.stats["errors"] += 1
                return None
        except queue.Empty:
            return None

    def scan_for_peers(self, duration: float = 5.0) -> List[str]:
        """Scan for other Scimitar devices"""
        print(f"[BT LE] Scanning for {duration}s...")
        # Simulated peer discovery
        self._peers = ["SCIM_DEVICE_001", "SCIM_DEVICE_002"]
        return self._peers


class WiFiChannel(PhaseChannel):
    """
    WiFi (2.4GHz/5GHz) phase synchronization channel.
    Uses UDP multicast for phase data broadcast.
    """

    def __init__(self, device_id: str, band: str = "2.4GHz",
                 multicast_group: str = "239.255.255.250", port: int = 51843):
        super().__init__(device_id)
        self.frequency = band
        self.multicast_group = multicast_group
        self.port = port

        self._socket = None

    def connect(self) -> bool:
        """Initialize WiFi multicast socket"""
        try:
            # In real implementation, this would create UDP multicast socket
            self.connected = True
            print(f"[WiFi {self.frequency}] Multicast socket ready on {self.multicast_group}:{self.port}")
            return True
        except Exception as e:
            print(f"[WiFi] Connection failed: {e}")
            self.stats["errors"] += 1
            return False

    def disconnect(self) -> None:
        """Close WiFi multicast socket"""
        if self._socket:
            self._socket = None
        self.connected = False
        print(f"[WiFi {self.frequency}] Socket closed")

    def transmit(self, packet: PhasePacket) -> bool:
        """Broadcast phase packet via UDP multicast"""
        if not self.connected:
            return False

        try:
            data = packet.to_bytes()
            # In real implementation, this would sendto() on multicast socket
            self.stats["packets_sent"] += 1
            self.tx_queue.put(packet)
            return True
        except Exception as e:
            print(f"[WiFi] Transmit error: {e}")
            self.stats["errors"] += 1
            return False

    def receive(self, timeout: float = 1.0) -> Optional[PhasePacket]:
        """Receive phase packet from UDP multicast"""
        if not self.connected:
            return None

        try:
            packet = self.rx_queue.get(timeout=timeout)
            if packet.validate():
                self.stats["packets_received"] += 1
                return packet
            else:
                self.stats["errors"] += 1
                return None
        except queue.Empty:
            return None


class RFChannel(PhaseChannel):
    """
    RF (433MHz/915MHz) phase synchronization channel.
    Uses LoRa-style modulation for long-range phase sync.
    """

    def __init__(self, device_id: str, frequency: str = "433MHz",
                 spreading_factor: int = 7, bandwidth: int = 125000):
        super().__init__(device_id)
        self.frequency = frequency
        self.spreading_factor = spreading_factor
        self.bandwidth = bandwidth

        # Calculate RF parameters
        self.freq_hz = 433e6 if frequency == "433MHz" else 915e6

    def connect(self) -> bool:
        """Initialize RF transceiver"""
        try:
            # In real implementation, this would configure SX127x or similar
            self.connected = True
            print(f"[RF {self.frequency}] Transceiver ready, SF={self.spreading_factor}, BW={self.bandwidth}Hz")
            return True
        except Exception as e:
            print(f"[RF] Connection failed: {e}")
            self.stats["errors"] += 1
            return False

    def disconnect(self) -> None:
        """Close RF transceiver"""
        self.connected = False
        print(f"[RF {self.frequency}] Transceiver closed")

    def transmit(self, packet: PhasePacket) -> bool:
        """Transmit phase packet via RF modulation"""
        if not self.connected:
            return False

        try:
            data = packet.to_bytes()
            # In real implementation, this would transmit via LoRa
            self.stats["packets_sent"] += 1
            self.tx_queue.put(packet)
            return True
        except Exception as e:
            print(f"[RF] Transmit error: {e}")
            self.stats["errors"] += 1
            return False

    def receive(self, timeout: float = 1.0) -> Optional[PhasePacket]:
        """Receive phase packet from RF"""
        if not self.connected:
            return None

        try:
            packet = self.rx_queue.get(timeout=timeout)
            if packet.validate():
                self.stats["packets_received"] += 1
                self.stats["last_rssi"] = -80  # Simulated RSSI
                return packet
            else:
                self.stats["errors"] += 1
                return None
        except queue.Empty:
            return None

    def get_rssi(self) -> int:
        """Get last received signal strength"""
        return self.stats["last_rssi"]


class ChannelManager:
    """Manages multiple Scimitar-SSE communication channels"""

    def __init__(self, device_id: str):
        self.device_id = device_id
        self.channels: Dict[str, PhaseChannel] = {}
        self.active = False

    def add_bluetooth(self) -> BluetoothLEChannel:
        """Add Bluetooth LE channel"""
        channel = BluetoothLEChannel(self.device_id)
        self.channels["bluetooth_le"] = channel
        return channel

    def add_wifi(self, band: str = "2.4GHz") -> WiFiChannel:
        """Add WiFi channel"""
        key = f"wifi_{band.replace('.', '_').replace('GHz', '')}"
        channel = WiFiChannel(self.device_id, band=band)
        self.channels[key] = channel
        return channel

    def add_rf(self, frequency: str = "433MHz") -> RFChannel:
        """Add RF channel"""
        key = f"rf_{frequency.replace('MHz', '')}"
        channel = RFChannel(self.device_id, frequency=frequency)
        self.channels[key] = channel
        return channel

    def connect_all(self) -> Dict[str, bool]:
        """Connect all channels"""
        results = {}
        for name, channel in self.channels.items():
            results[name] = channel.connect()
        self.active = any(results.values())
        return results

    def disconnect_all(self) -> None:
        """Disconnect all channels"""
        for channel in self.channels.values():
            channel.disconnect()
        self.active = False

    def broadcast(self, packet: PhasePacket) -> Dict[str, bool]:
        """Broadcast packet on all connected channels"""
        results = {}
        for name, channel in self.channels.items():
            if channel.connected:
                results[name] = channel.transmit(packet)
        return results

    def get_all_stats(self) -> Dict[str, Dict]:
        """Get statistics from all channels"""
        return {name: channel.get_stats() for name, channel in self.channels.items()}


if __name__ == "__main__":
    print("=" * 60)
    print("SCIMITAR-SSE v7.1 - CHANNEL TEST")
    print("=" * 60)

    # Create channel manager
    manager = ChannelManager("SCIM_TEST_001")

    # Add all channels
    manager.add_bluetooth()
    manager.add_wifi("2.4GHz")
    manager.add_wifi("5GHz")
    manager.add_rf("433MHz")
    manager.add_rf("915MHz")

    # Connect all
    results = manager.connect_all()
    print(f"\nConnection results: {results}")

    # Create test packet
    bt_channel = manager.channels["bluetooth_le"]
    packet = bt_channel.create_packet(
        group_a_phase=0.5,
        group_b_phase=-0.5,
        coherence=0.95,
        decoherence=0.05
    )
    print(f"\nTest packet created:")
    print(f"  Sequence: {packet.sequence_id}")
    print(f"  Checksum: {packet.checksum}")
    print(f"  Valid: {packet.validate()}")

    # Broadcast
    broadcast_results = manager.broadcast(packet)
    print(f"\nBroadcast results: {broadcast_results}")

    # Get stats
    stats = manager.get_all_stats()
    print(f"\nChannel statistics:")
    for name, stat in stats.items():
        print(f"  {name}: {stat}")

    # Cleanup
    manager.disconnect_all()
    print("\nAll channels disconnected")
