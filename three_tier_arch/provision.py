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
                        if output['OutputKey'] == mapping['output']:
                            parameter['ParameterValue'] = output['OutputValue']
    return json.dumps(parameters_list)


def create_tier(stack_name, template_file, parameters_list, client):
    template_string = read_conf(template_file)
    try:
        stack_id = client.create_stack(
            StackName=stack_name,
            TemplateBody=template_string,
            Parameters=parameters_list)
        return stack_id
    except Exception as e:
        if type(e).__name__ == "AlreadyExistsException":
            response = client.describe_stacks(
                StackName=stack_name)
            stacks = response['Stacks']
            if len(stacks) == 1:
                stack_id = stacks[0]['StackId']
                return stack_id
            else:
                raise Exception('Stack with name[' + stack_name + "'] exists, but cannot be queried.")
        else:
            print("caught exception: "+str(e)+"!")
            raise e


def create_infrastructure(infrastructure_file, client):
    infrastructure_string = read_conf(infrastructure_file)
    infrastructure_json = json.loads(infrastructure_string)
    for tier in infrastructure_json['stacks']:
        print("CREATING " + tier['name'] + " with template file " + tier['template_file'] + " and parameters file " +
              tier['parameters_file'])
        if len(tier['dependencies']) > 0:
            print("Tier " + tier['name'] + " has " + str(len(tier['dependencies'])) + " dependencies, resolving ...")
            parameters_list = json.loads(resolve_dependencies(tier['parameters_file'], tier['dependencies'], client))
        else:
            print("Tier " + tier['name'] + " has no dependencies")
            parameters_list = json.loads(read_conf(tier['parameters_file']))
        stack = tier['name']
        create_tier(stack, tier['template_file'], parameters_list, client)
        status = str(get_status_of_stack(stack, client))
        while status != 'CREATE_COMPLETE':
            time.sleep(10)
            status = str(get_status_of_stack(stack, client))
            if status == "CREATE_FAILED" or status.startswith("ROLLBACK"):
                print("ERROR Create Failed with status: " + status + ", please manually remove this stack.")
                return
            else:
                print("Creating " + stack + " ... current status " + status)

        print(stack + " created! ")


def main():
    client = boto3.client('cloudformation')
    create_infrastructure(INFRASTRUCTURE_FILE, client)


if __name__ == '__main__':
    main()
