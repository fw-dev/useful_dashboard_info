
class ClientCompliance:
    # 0 - zero errors, all ok
    # 1 - unknown, not enough information
    # 2 - warning, something isn't quite right
    # 3 - critical, something definately is wrong
    STATE_OK = 0
    STATE_UNKNOWN = 1
    STATE_WARNING = 2
    STATE_ERROR = 3

    def __init__(self, total_disk, free_disk, last_checkin_days, outstanding_critical_patches=-1, outstanding_standard_patches=-1):
        self.total_disk = total_disk
        self.free_disk = free_disk
        self.last_checkin_days = last_checkin_days
        self.outstanding_critical_patches = outstanding_critical_patches
        self.outstanding_standard_patches = outstanding_standard_patches

    def get_patch_compliance(self):
        if self.outstanding_critical_patches == 0 and self.outstanding_standard_patches == 0:
            return ClientCompliance.STATE_OK

        if self.outstanding_critical_patches > 0:
            return ClientCompliance.STATE_ERROR

        if self.outstanding_standard_patches > 0:
            return ClientCompliance.STATE_WARNING

        return ClientCompliance.STATE_UNKNOWN

    def get_checkin_compliance(self):
        if self.last_checkin_days is None:
            return ClientCompliance.STATE_UNKNOWN
        if self.last_checkin_days < 7:
            return ClientCompliance.STATE_OK
        if self.last_checkin_days < 14:
            return ClientCompliance.STATE_WARNING
        return ClientCompliance.STATE_ERROR

    def get_disk_compliance(self):
        if self.free_disk is None or self.total_disk is None:
            return ClientCompliance.STATE_UNKNOWN

        # < 20% left is warning
        # < 5% left is critical, or less than 5g
        space_compliance = ClientCompliance.STATE_UNKNOWN
        if self.free_disk > 0 and self.total_disk > 0:
            space_left_pcnt = (float(self.free_disk) / float(self.total_disk)) * 100.0

            if space_left_pcnt >= 20:
                space_compliance = ClientCompliance.STATE_OK
            elif space_left_pcnt < 5:
                space_compliance = ClientCompliance.STATE_ERROR
            else:
                space_compliance = ClientCompliance.STATE_WARNING  # its just less than 20

        return space_compliance

    def get_compliance_state(self):
        checkin = self.get_checkin_compliance()
        disk = self.get_disk_compliance()
        patch = self.get_patch_compliance()
        return max(checkin, disk, patch)

    @staticmethod
    def get_compliance_state_str(state_value):
        mappings = {
            0: "Unknown",
            1: "Ok",
            2: "Warning",
            3: "Error"
        }

        return mappings[state_value]
