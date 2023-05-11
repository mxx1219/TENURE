import os

if __name__ == "__main__":
    with open("config.txt", "r") as file:
        content = file.readlines()
    config = {}
    for line in content:
        key = line.split(":")[0].strip()
        value = line.split(":")[1].strip()
        config[key] = value

    cmd = "cd ./scripts/ && python3 solve_strings.py {} {} {}"\
        .format(config["d4j_version"], config["bug_version"], config["fl_setting"])
    os.system(cmd)

    cmd = "cd ./scripts/ && python3 parse_global_info.py {} {} {}"\
        .format(config["d4j_version"], config["bug_version"], config["fl_setting"])
    os.system(cmd)
    
    cmd = "cd ./scripts/ && python3 parse_necessary_info.py {} {} {}" \
        .format(config["d4j_version"], config["bug_version"], config["fl_setting"])
    os.system(cmd)
    
    cmd = "cd ./scripts/ && python3 get_package.py {} {} {}" \
        .format(config["d4j_version"], config["bug_version"], config["fl_setting"])
    os.system(cmd)
    
    
    cmd = "cd ./scripts/ && python3 nmt_predict.py {} {} {} {} {}" \
        .format(config["d4j_version"], config["bug_version"], config["fl_setting"],
                config["beam_35"], config["beam_single"])
    os.system(cmd)

    cmd = "cd ./scripts/ && python3 combine.py {} {} {} {} {}" \
        .format(config["d4j_version"], config["bug_version"], config["fl_setting"],
                config["beam_35"], config["beam_single"])
    os.system(cmd)

    cmd = "cd ./tool_set/prt/ && python3 prt.py {} {} {} {}" \
        .format(config["d4j_version"], config["bug_version"], config["fl_setting"],
                config["beam_all"])
    os.system(cmd)
    
    '''
    cmd = "cd ./tool_set/urt/ && python3 urt.py {} {} {} {}" \
        .format(config["d4j_version"], config["bug_version"], config["fl_setting"],
                config["beam_all"])
    os.system(cmd)
        
    cmd = "cd ./tool_set/pct/ && python3 pct.py {} {} {} {} {} {}" \
        .format(config["d4j_version"], config["bug_version"], config["fl_setting"],
                config["beam_all"], config["beam_35"], config["beam_single"])
    os.system(cmd)
    
    cmd = "cd ./scripts/ && python3 get_meta_info.py {} {} {}" \
        .format(config["d4j_version"], config["bug_version"], config["fl_setting"])
    os.system(cmd)

    cmd = "cd ./scripts/ && python3 parse_special.py {} {} {}" \
        .format(config["d4j_version"], config["bug_version"], config["fl_setting"])
    os.system(cmd)
 
    cmd = "cd ./patch_validation/ && python3 validate.py {} {} {} {}" \
        .format(config["d4j_version"], config["bug_version"], config["fl_setting"],
                config["beam_all"])
    os.system(cmd)

    print("Repair process end.")
    '''
