# NFA ShotGrid Project Creator tool by Gilles Vink
import re
from shotgun_api3 import shotgun
import os
import datetime
import urllib3
import requests
import webbrowser


class ProjectCreation:
    def __init__(self):
        print("NFA ShotGrid Project Creator")
        print("\n")
        print("Tool is starting... Please wait.")

        # Set here your credentials
        self.sg = shotgun.Shotgun(
            "https://nfa.shotgunstudio.com",
            script_name="****",
            api_key="****",
        )

        print("Successfully connected to ShotGrid servers.")
        print("\n")

        # If user is validated, start project creation
        if self.__get_user():
            self.create_project()

        input(
            "Press 'enter' to continue... Or just look at this beautiful command prompt window :)"
        )

    def create_project(self):
        # Project name
        project_name = self.project_name()

        # Project code
        project_code = self.project_code()

        # Supervisors
        supervisors = self.supervisors()
        supervisor_ids = supervisors[0]
        supervisor_names = supervisors[1]

        # Render engine
        render_engine = self.render_engines()

        # Project type
        project_type = self.project_type()

        # FPS
        fps = self.fps()

        # Validate settings for project creation
        if self.project_settings(
                project_name=project_name,
                project_code=project_code,
                supervisors=supervisor_names,
                render_engine=render_engine,
                fps=fps,
        ):
            print("Starting project creation for '%s'." % project_name)

            # Starting submission with all set variables
            try:
                project = self.__setup_project(
                    project_name=project_name,
                    project_code=project_code,
                    render_engine=render_engine,
                    project_type=project_type,
                    fps=fps,
                    supervisor_ids=supervisor_ids,
                    student_year=self.student_year,
                    graduation_year=self.student_graduation_year,
                )

                # Set correct permission groups
                try:
                    for supervisor in supervisor_ids:
                        self.__update_user_permissions(supervisor)

                except Exception as e:
                    print(
                        "Something went wrong while updating the user settings. "
                        "Please contact a pipeline administrator."
                    )

                print("Project '%s' successfully created" % project_name)

                # Launch project in webbrowser
                self.__open_project(project)

                print(
                    "You can now open and edit the project on https://nfa.shotgunstudio.com/ (which is also opened for you currently) "
                    "or open software via ShotGrid desktop (please remember to refresh)."
                )

            except Exception as e:
                print("Something went wrong. Please contact the pipline administrator.")
                print(str(e))

        else:
            print(
                "Project creation cancelled. You can restart this program to create a project."
            )

    # Ask user for project name, and validate name
    def project_name(self):
        print("How would you like to name the project?")
        validated = False

        project_name = ""

        while validated is False:
            project_name = input()
            validated = self.__validate_projectname(project_name)

            if not validated:
                print(
                    "Project name is incorrect or already existing. Please only use lowercase and underscores."
                )

        print("Project name: %s" % str(project_name))
        print("\n")

        return project_name

    # Validates name for correct naming convention
    def __validate_projectname(self, project_name):
        validated = False

        regex = "^[a-z_]*$"
        match = re.match(regex, project_name)

        if match:
            # Search for project name
            project_search = [["name", "is", project_name]]
            project = self.sg.find_one("Project", project_search)

            if project is None:
                validated = True

        return validated

    # Ask user for project code, and validate code
    def project_code(self):
        print("What would be the project code? (3 letters)")
        validated = False

        project_code = ""

        while validated is False:
            project_code = input()
            validated = self.__validate_projectcode(project_code)

            if not validated:
                print(
                    "Project code is incorrect or already existing. Only use 3 letters in lowercase."
                )

        print("Project code: %s" % str(project_code))
        print("\n")

        return project_code

    # Validates name for correct naming convention
    def __validate_projectcode(self, project_code):
        validated = False

        if len(project_code) == 3:
            regex = "^[a-z_]*$"
            match = re.match(regex, project_code)

            if match:
                projectcode_search = [["sg_projectcode", "is", project_code]]
                projectcode = self.sg.find_one("Project", projectcode_search)

                if projectcode is None:
                    validated = True

        return validated

    # Search for other supervisors on the ShotGrid user database
    def supervisors(self):
        print(
            "Are there, besides you, other supervisors on this project? Type [Y]es or [N]o"
        )
        validated = False

        supervisor_ids = []
        supervisor_names = []
        supervisor_ids.append(self.sg_user_id)
        supervisor_names.append(self.sg_username)

        answer = ""

        while validated is False:
            answer = input()
            validated = self.__validate_boolean(answer)

            if not validated:
                print(
                    "Please choose [Y]es or [N]o. (Just the letter 'Y' for yes or 'N' for no)"
                )

        # If user says yes, then go through all the options
        if answer.lower() == "y":
            more_supervisors = True
            while more_supervisors is True:
                found_supervisor = self.__find_supervisor()
                found_supervisor_id = found_supervisor[0]
                found_supervisor_name = found_supervisor[1]

                # If the user is not already in the supervisor id's, add the supervisor to the supervisor list
                if not found_supervisor_id in supervisor_ids:
                    supervisor_ids.append(found_supervisor_id)
                    supervisor_names.append(found_supervisor_name)
                    print(
                        "Added %s to the list of supervisors." % found_supervisor_name
                    )
                    print("\n")

                else:
                    print(
                        "%s is already in the list of supervisors for this project. Please choose someone else "
                        "or proceed." % found_supervisor_name
                    )
                    print("\n")

                print("Do you want to add another supervisor? Type [Y]es or [N]o")

                validated = False

                while validated is False:
                    answer = input()
                    validated = self.__validate_boolean(answer)

                    if not validated:
                        print(
                            "Please choose [Y]es or [N]o. (Just the letter 'Y' for yes or 'N' for no)"
                        )

                if answer.lower() == "n":
                    print("Supervisors: %s" % supervisor_names)
                    return supervisor_ids, supervisor_names

        else:
            print("No other supervisors beside you on this project, roger that!")
            print("\n")
            return supervisor_ids, supervisor_names

    # Find other users on the ShotGrid database
    def __find_supervisor(self):
        while True:
            print("Please type the name (just a part of the name to find him/her).")
            name = input()

            found_user = self.__find_user(name)
            if found_user:
                found_user_name = found_user.get("name")
                found_user = found_user.get("id")

                print("Do you mean %s? Type [Y]es or [N]o" % found_user_name)
                validated = False
                while validated is False:
                    answer = input()
                    print("\n")
                    validated = self.__validate_boolean(answer)

                    if not validated:
                        print(
                            "Please choose [Y]es or [N]o. (Just the letter 'Y' for yes or 'N' for no)"
                        )

                if answer.lower() == "y":
                    return found_user, found_user_name

            else:
                print("Did not find %s, please try again." % name)

    # Ask the user the render engine to use, this will later set the environment for launching software.
    def render_engines(self):
        print(
            "What is the render engine to be used? \n 1. All \n 2. Arnold \n 3. RenderMan"
        )
        validated = False

        render_engine = ""

        while validated is False:
            render_engine = input()
            validated = self.__validate_renderengine(render_engine)

            if not validated:
                print("Render engine is incorrect, choose 1, 2 or 3.")

        if render_engine == "1":
            render_engine_name = "All"

        elif render_engine == "2":
            render_engine_name = "Arnold"

        else:
            render_engine_name = "RenderMan"

        print("Render engine: %s" % str(render_engine_name))
        print("\n")

        return render_engine_name

    # Validates name for correct naming convention
    @staticmethod
    def __validate_renderengine(render_engine):
        validated = False
        try:
            render_engine = int(render_engine)
        except:
            return False
        if render_engine > 0 and render_engine < 4:
            validated = True

        return validated

    # Ask the user what type the project will be
    def project_type(self):
        print("What is the project type? \n 1. Fiction \n 2. Documentary")
        validated = False

        project_type = ""

        while validated is False:
            project_type = input()
            validated = self.__validate_projecttype(project_type)

            if not validated:
                print("Project type is incorrect, choose 1 or 2.")

        if project_type == "1":
            project_type_name = "Fiction"

        else:
            project_type_name = "Documentary"

        print("Project type: %s" % str(project_type_name))
        print("\n")

        return project_type_name

    # Validates name for correct naming convention
    @staticmethod
    def __validate_projecttype(project_type):
        validated = False
        try:
            project_type = int(project_type)
        except:
            return False
        if project_type > 0 and project_type < 3:
            validated = True

        return validated

    # Ask the user what the FPS for the project will be
    def fps(self):
        print("What is the FPS for the project? (Only digits, like 25 for 25fps)")
        validated = False

        while validated is False:
            fps = input()
            validated = self.__validate_fps(fps)

            if not validated:
                print("FPS is incorrect, only use digits, like 25")

        print("FPS: %s fps" % str(fps))
        print("\n")

        return fps

    # Validates name for correct naming convention
    @staticmethod
    def __validate_fps(fps):
        validated = False
        if len(fps) > 1:
            try:
                fps = int(fps)
            except Exception as e:
                return False

            validated = True

        return validated

    # Return all project settings to use, and if returned "no", then stop the project creation
    def project_settings(
            self, project_name, project_code, supervisors, render_engine, fps
    ):
        print("You choose the following settings for the project:")
        print("Project name: %s" % project_name)
        print("Project code: %s" % project_code)
        print("Supervisors: %s" % supervisors)
        print("Render engine: %s" % render_engine)
        print("FPS: %s" % fps)
        print(
            "Are you sure you want to create the project with these settings? Type [Y]es or [N]o"
        )
        validated = False

        while validated is False:
            answer = input()
            validated = self.__validate_boolean(answer)

            if not validated:
                print(
                    "Please choose [Y]es or [N]o. (Just the letter 'Y' for yes or 'N' for no)"
                )

        proceed_creation = False

        if answer.lower() == "y":
            proceed_creation = True

        print("\n")

        return proceed_creation

    # Validates name for correct naming convention
    def __validate_boolean(self, answer):
        validated = False

        if len(answer) == 1:
            if answer.lower() == "y" or answer.lower() == "n":
                validated = True

        return validated

    # Get the current user, and check if the user exists on ShotGrid
    def __get_user(self):
        username = os.getlogin()

        # Simple bypass to allow use on non user pc's
        if username == "VFXIM":
            username = "Gilles.Vink"

        # Build filters
        columns = ["name"]
        search_user = [["login", "is", username]]

        # Find the user
        sg_user = self.sg.find_one("HumanUser", search_user, columns)

        # If no user is found, return a error
        if sg_user is None:
            print(
                "Could not find user %s on ShotGrid. Please contact a pipeline administrator."
                % username
            )
            return False

        self.sg_username = sg_user.get("name")

        self.sg_user_id = sg_user.get("id")

        # Get the student year from the current student according to ShotGrid database
        student_data = self.__get_student_year(self.sg_user_id)

        self.student_year = student_data[0]
        self.student_graduation_year = student_data[1]

        # Found user! Now let's welcome the user :)
        print("Welcome %s :) " % self.sg_username)

        return True

    # Look into the database to collect the student year, and
    # automatically adjust it after summer to match year transition
    def __get_student_year(self, id):
        # Get user data
        filters = [["id", "is", id]]
        columns = ["sg_lichting"]

        # Get current year
        sg_user_data = self.sg.find_one("HumanUser", filters, columns)
        graduation_year = sg_user_data.get("sg_lichting")
        sg_lichting = graduation_year[1:]
        sg_lichting = int(sg_lichting)

        current_time = datetime.datetime.now()
        corrected_time = current_time + datetime.timedelta(days=120)

        current_year = int(corrected_time.strftime("%Y"))

        to_graduation_year = sg_lichting - current_year

        if to_graduation_year == 0:
            student_year = 4

        elif to_graduation_year == 1:
            student_year = 3

        else:
            student_year = 2

        return student_year, graduation_year

    # Here we will create the project with all specified variables
    def __setup_project(
            self,
            project_name,
            project_code,
            render_engine,
            project_type,
            fps,
            supervisor_ids,
            student_year,
            graduation_year,
    ):
        supervisors = []
        for supervisor in supervisor_ids:
            supervisors.append({"id": supervisor, "type": "HumanUser"})

        project_data = {
            "name": project_name,
            "tank_name": project_name,
            "sg_projectcode": project_code,
            "users": supervisors,
            "sg_supervisors": supervisors,
            "sg_render_engine": render_engine,
            "sg_type": project_type,
            "sg_lichting": graduation_year,
            "sg_fps": int(fps),
            "sg_status": "Active",
        }
        created_project = self.sg.create("Project", project_data)

        print("Created ShotGrid project, now adding pipeline configuration.")
        print("\n")

        project_id = created_project.get("id")

        descriptor = self.__get_descriptor(student_year)

        descriptor_lichting = "s" + str(student_year)

        pipeline_configuration_data = {
            "code": "Primary",
            "descriptor": descriptor,
            "plugin_ids": "basic.*",
            "project": {"id": project_id, "type": "Project"},
            "sg_lichting": descriptor_lichting,
        }

        self.sg.create("PipelineConfiguration", pipeline_configuration_data)

        print("Created pipeline configuration.")
        print("\n")

        return project_id

    # Request the latest published pipeline configuration from ShotGrid to use according to student year
    @staticmethod
    def __get_descriptor(student_year):
        latest_release = requests.get(
            "https://api.github.com/repos/nfa-vfxim/nfa-shotgun-configuration/releases/latest"
        )
        latest_release = latest_release.json()["name"]

        release_length = len(latest_release)
        if latest_release.endswith("s4"):
            latest_release = latest_release[: release_length - 2]

        elif latest_release.endswith("s3"):
            latest_release = latest_release[: release_length - 2]

        elif latest_release.endswith("s2"):
            latest_release = latest_release[: release_length - 2]

        print("Latest pipeline release is %s." % latest_release)
        print("\n")

        descriptor = (
                "sgtk:descriptor:git?path=https://github.com/nfa-vfxim/nfa-shotgun-configuration.git&version="
                + latest_release
                + "s"
                + str(student_year)
        )

        return descriptor

    # Update the user with the supervision permissions
    def __update_user_permissions(self, id):
        filters = [["id", "is", id]]
        columns = ["permission_rule_set", "name"]

        # Get current year
        current_permission = self.sg.find_one("HumanUser", filters, columns)
        user_name = current_permission.get("name")
        current_permission = current_permission.get("permission_rule_set")
        current_permission = current_permission.get("name")

        if current_permission == "Admin":
            print("%s is an admin, skipping user settings." % user_name)
            print("\n")

        elif current_permission == "Artist":
            user_data = {
                "permission_rule_set": {
                    "id": 190,
                    "name": "Supervisor",
                    "type": "PermissionRuleSet",
                }
            }
            self.sg.update("HumanUser", id, user_data)

            print("Updated user settings for %s." % user_name)
            print("\n")

        else:
            print(
                "%s already has different settings, skipping updating user permissions."
                % user_name
            )
            print("\n")

    # Find user according to name
    def __find_user(self, name):
        filters = [["name", "contains", name]]
        columns = ["name"]

        sg_user_data = self.sg.find_one("HumanUser", filters, columns)

        return sg_user_data

    # Open the project in webbrowser according to id
    def __open_project(self, id):
        url = "https://nfa.shotgunstudio.com/page/project_overview?project_id=" + str(
            id
        )
        webbrowser.open(url, new=2)


# When this script is run, run the main class
ProjectCreation()
