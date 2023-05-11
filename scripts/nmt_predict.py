import os
import sys
import torch


def solve_resize(patch_path, BEAM, BEAM_COVER):
    resize_patch_irs = []
    with open(patch_path, "r") as file:
        patch_irs = file.readlines()
        patch_irs = [line.strip() for line in patch_irs]
    stmts = len(patch_irs) // BEAM_COVER
    for i in range(stmts):
        resize_patch_irs += patch_irs[i*BEAM_COVER: i*BEAM_COVER+BEAM]
    os.remove(patch_path)
    with open(patch_path, "w") as file:
        file.write("\n".join(resize_patch_irs))


if __name__ == "__main__":
    d4j_version = sys.argv[1]
    bug_version = sys.argv[2]
    fl_setting = sys.argv[3]
    BEAM_35 = int(sys.argv[4].strip())
    BEAM_single = int(sys.argv[5].strip())
    BEAM_35_COVER = 500 if BEAM_35 <= 500 else BEAM_35
    BEAM_single_COVER = 500 if BEAM_single <= 500 else BEAM_single
    use_gpu = torch.cuda.is_available()

    nmt_origin_dir = os.path.abspath("../nmt_model/origin_onmt/")
    nmt_combine_dir = os.path.abspath("../nmt_model/joint_inference/")
    check_point_dir = os.path.join(nmt_origin_dir, "check_point/")
    src_path = os.path.abspath("../parsed_data/d4j_{}/{}/{}/completion_info/src.txt"
                               .format(d4j_version, fl_setting, bug_version))

    origin_out_dir = os.path.join(nmt_origin_dir, "d4j_result/d4j_{}/{}/{}/".format(d4j_version, fl_setting, bug_version))
    if not os.path.exists(origin_out_dir):
        os.makedirs(origin_out_dir)
    
    for part in ["copy_35", "copy_single"]:
        BEAM = BEAM_35 if part.endswith("35") else BEAM_single
        BEAM_COVER = BEAM_35_COVER if part.endswith("35") else BEAM_single_COVER
        cmd = "cd {} && python3 translate.py -model {} -src {} "\
              "-output {} -batch_size 1 -beam_size {} -n_best {} {}"\
            .format(nmt_origin_dir, os.path.join(check_point_dir, part, "saved_model.pt"),
                    src_path, os.path.join(origin_out_dir, "{}.txt".format(part)), BEAM_COVER, BEAM_COVER, "-gpu 0" if use_gpu else "")
        os.system(cmd)
        if BEAM != BEAM_COVER:
            solve_resize(os.path.join(origin_out_dir, "{}.txt".format(part)), BEAM, BEAM_COVER)

    combine_out_dir = os.path.join(nmt_combine_dir, "d4j_result/d4j_{}/{}/{}/".format(d4j_version, fl_setting, bug_version))
    if not os.path.exists(combine_out_dir):
        os.makedirs(combine_out_dir)
    for part in ["combine_35", "combine_single"]:
        BEAM = BEAM_35 if part.endswith("35") else BEAM_single
        BEAM_COVER = BEAM_35_COVER if part.endswith("35") else BEAM_single_COVER
        copy_model_dir = "copy_35" if part.endswith("35") else "copy_single"
        nocopy_model_dir = "nocopy_35" if part.endswith("35") else "nocopy_single"
        cmd = "cd {} && python3 translate.py -model {} -model_tmp {} -src {} "\
              "-output {} -batch_size 1 -beam_size {} -n_best {} {}"\
            .format(nmt_combine_dir, os.path.join(check_point_dir, copy_model_dir, "saved_model.pt"),
                    os.path.join(check_point_dir, nocopy_model_dir, "saved_model.pt"),
                    src_path, os.path.join(combine_out_dir, "{}.txt".format(part)), BEAM_COVER, BEAM_COVER, "-gpu 0" if use_gpu else "")
        os.system(cmd)
        if BEAM != BEAM_COVER:
            solve_resize(os.path.join(combine_out_dir, "{}.txt".format(part)), BEAM, BEAM_COVER)
    
