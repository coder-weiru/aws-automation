import json
import time
import boto3
import boto3.exceptions

REGION = 'us-east-1'
INFRASTRUCTURE_FILE = './infrastructure.json'


def read_conf(path):
    with open(path, 'r') as f:
        return f.read()


def get_status_of_stack(stack, client):
    describe_of_stack = client.describe_stacks(
        StackName=stack
    )["Stacks"][0]
    return describe_of_stack["StackStatus"]


def get_output_of_stack(stack, client):
    describe_of_stack: object = client.describe_stacks(
        StackName=stack
    )["Stacks"][0]
    return describe_of_stack["Outputs"]


def resolve_dependencies(parameters_file, dependencies, client):
    parameters_string = read_conf(parameters_file)
    parameters_list = json.loads(parameters_string)
    for parameter in parameters_list:
        for depend in dependencies:
            for mapping in depend['mapping']:
                if parameter['ParameterKey'] == mapping['input']:
                    for output in get_output_of_stack(depend['stack'], client):
                        if output.key == mapping['output']:
                            parameter['ParameterValue'] = output.value
    return json.dumps(parameters_list)


def delete_tier(stack_name, client):
    try:
        stack_id = client.delete_stack(
            StackName=stack_name)
        return stack_id
    except Exception as ex:
        print(str(ex))
        raise ex


def delete_infrastructure(infrastructure_file, client):
    infrastructure_string = read_conf(infrastructure_file)
    infrastructure_json = json.loads(infrastructure_string)
    for tier in infrastructure_json['stacks']:
        print("DELETING " + tier['name'] + " with template file " + tier['template_file'] + " and parameters file " +
              tier['parameters_file'])
        stack = tier['name']
        delete_tier(stack, client)
        status = str(get_status_of_stack(stack, client))
        while status != 'DELETE_COMPLETE':
            time.sleep(10)
            try:
                status = str(get_status_of_stack(stack, client))
            except Exception as ex:
                if ex.__str__().__contains__("does not exist"):
                    break
                else:
                    raise ex

            if status == "DELETE_FAILED" or status.startswith("ROLLBACK"):
                print("ERROR Delete Failed")
                return
            else:
                print("Deleting " + stack + " ... current status " + status)

        print(stack + " deleted! ")


def main():
    client = boto3.client('cloudformation')
    delete_infrastructure(INFRASTRUCTURE_FILE, client)


if __name__ == '__main__':
    main()
