"""
This test is used to see if the structure of a NeXus
definition has been properly encoded
"""
import json


def explore_structure(
        parent: dict,
        current_path:str = ""
):
    for name, infos in parent.items():
        assert isinstance(name, str)

        info_list = {
            "element type": False,
            "type": False,
            "docstring": False,
            "value": False,
            "possible value": False,
            "EX_required": False,
            "content": False
        }

        current_path = current_path + name
        info_number = 0
        for key, value in infos.items():
            assert isinstance(key, str)
            if key in ["element type", "type", "docstring"]:
                assert isinstance(value, str)
            elif key == "value":
                assert value is None or isinstance(value, str)
            elif key == "possible value":
                assert isinstance(value, list) or value is None
            elif key == "EX_required":
                assert isinstance(value, bool)
            elif key == "content":
                assert isinstance(value, dict) or value is None
                if value is not None and not name.startswith("@"):
                    explore_structure(value, current_path)
            else:
                raise KeyError(f"{key}, in {current_path} is not supported")
            info_list[key] = True
            info_number += 1

        if info_number != 7:
            missing_info = ""
            for info, state in info_list.items():
                if not state:
                    missing_info += f"{info}, "
            raise Exception(f"The following info are missing in {current_path}:\n{missing_info}")
    return True


def test_structure():
    path_file_to_test = r""

    with open(path_file_to_test, "r") as structure:
        main_dict = json.load(structure)

    assert explore_structure(main_dict)