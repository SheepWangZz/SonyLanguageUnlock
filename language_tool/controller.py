"""Bind the visible selection to a fresh device query and fixed write profile."""
from . import detection, firmware, workflow, fonts
from .i18n import UserError


def execute(device, chinese, package, log=lambda message: None,
            detector=None, apply=workflow.apply):
    firmware.check_selection(device, chinese, package)
    firmware.require_supported(device)
    current = detector() if detector is not None else detection.detect(log=log)
    if any(current.get(k) != device.get(k) for k in ('model', 'version', 'body_digest')):
        raise UserError('device_changed')
    firmware.check_selection(current, chinese, package)
    # fonts.load hashes the actual selected file again and extracts only the
    # reviewed resources before service mode. No cached font bytes are trusted.
    if chinese and package['sha256'] != fonts.DAT_SHA:
        raise UserError('package_unverified')
    return apply(chinese, source=package['path'] if chinese else None,
                 log=log, expected_identity=current['body_digest'])
