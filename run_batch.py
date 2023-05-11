import os
import random
import sys

if __name__ == "__main__":
    host = int(sys.argv[1])
    with open("./projects/v1.txt", "r") as file:
        versions = file.readlines()
        versions = [factor.strip() for factor in versions]
    random.seed(666)
    random.shuffle(versions)
    step = (len(versions) - 1) // 10 + 1
    versions = versions[(host-1)*step: host*step]
    for version in versions:
        with open("./configs/{}.config".format(version), "r") as file:
            content = file.readlines()
        config = {}
        for line in content:
            key = line.split(":")[0].strip()
            value = line.split(":")[1].strip()
            config[key] = value
	
        # please use jdk 11
        cmd = "cd ./scripts/ && java -jar data_process.jar {} {} {}".format(config["d4j_version"], config["bug_version"], config["fl_setting"])
        os.system(cmd)
    
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
    
        print("{}: repair process end.".format(version))

