class FaultManager:

    @staticmethod
    def limit_fault(process, low_warning, low_shutdown, high_warning, high_shutdown):
        #flag array: low_warning, low_shutdown, high_warning, high_shutdown
        flag_list = [False, False, False, False]
        if process <= low_warning:
            flag_list[0] = True
            if process <= low_shutdown:
                flag_list[1] = True
        elif process >= high_warning:
            flag_list[2] = True
            if process >= high_shutdown:
                flag_list[3] = True
        else:
            flag_list = [False, False, False, False]
        return flag_list
        