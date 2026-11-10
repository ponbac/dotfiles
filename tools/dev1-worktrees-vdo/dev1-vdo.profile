# LVM metadata profile for dev-1's worktrees VDO pool (dev1data/vpool).
# Install: /etc/lvm/profile/dev1-vdo.profile (root:root 0644); used by `lvcreate --metadataprofile dev1-vdo`.
allocation {
	# Accept 16 MiB discards: fstrim of the volume takes ~7 s instead of ~60 s with the default 4 KiB.
	vdo_max_discard = 4096
}
activation {
	# dmeventd grows the pool by 20% whenever it passes 70% physical use, while the VG has free space.
	vdo_pool_autoextend_threshold = 70
	vdo_pool_autoextend_percent = 20
}
