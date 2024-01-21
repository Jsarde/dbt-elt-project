import time
import logging
import subprocess
# subprocess is a Python module that provides a way to execute system commands
# and interact with the shell from within a Python script


class ELT:
    def __init__(self) -> None:
        # set up logger
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

        # Postgres configurations
        self.source_config = {
            'dbname':'source_db',
            'user':'postgres',
            'password':'secret',
            # name of the service in docker-compose.yaml
            'host':'source_postgres'
        }
        self.destination_config = {
            'dbname':'destination_db',
            'user':'postgres',
            'password':'secret',
            'host':'destination_postgres'
        }

    def __wait_for_postgres(self, host: str, max_retries=5, retry_interval=5) -> bool:
        """
        INFO:
            Waits for Postgres to be ready by checking if it's accepting connections
        ARGS:
            host            (str): The Postgres host to connect to
            max_retries     (int): The maximum number of retries to attempt
            retry_interval  (int): The interval in seconds between retries
        RETURNS:
            bool: True if successfully connected to Postgres, False otherwise
        """
        retries = 1
        while retries < max_retries:
            try:
                self.logger.info('Waiting for Postgres to be ready...')
                result = subprocess.run(
                    # use the pg_isready command to check if Postgres is accepting connections
                    args=['pg_isready', '-h', host],
                    # if the command fails, a CalledProcessError exception will be raised
                    check=True,
                    # the output will be captured and returned as a byte string
                    capture_output=True,
                    # the output will be decoded to a string using the default system encoding
                    text=True
                )
                # stdout attribute is a byte string that contains the output of the command
                if 'accepting connections' in result.stdout:
                    self.logger.info('Successfully connected to Postgres :)')
                    return True
            except subprocess.CalledProcessError as e:
                self.logger.info(f'Error connecting to Postgres: {e}')
                retries += 1
                self.logger.info(
                    f'''Retrying in {retry_interval} seconds...
                    (Attempt {retries}/{max_retries})'''
                )
                time.sleep(retry_interval)
        self.logger.info('Failed to connect to Postgres. Exiting...')
        return False

    def __execute_dump_command(self, dump_command: list) -> None:
        """
        INFO:
            Executes the pg_dump command to dump the source database to a SQL file
        ARGS:
            dump_command (list): The pg_dump command to execute
        """
        self.logger.info('Dumping the source database to a SQL file...')
        source_subprocess_env = dict(PGPASSWORD=self.source_config['password'])
        try:
            # execute pg_dump command
            subprocess.run(
                args=dump_command,
                env=source_subprocess_env,
                check=True
            )
        except subprocess.CalledProcessError as e:
            self.logger.error(f'Error dumping the source database: {e}')
        else:
            self.logger.info('Successfully dumped the source database')

    def __execute_load_command(self, load_command: list) -> None:
        """
        INFO:
            Executes the psql command to load the SQL file into the destination database
        ARGS:
            load_command (list): The psql command to execute
        """
        self.logger.info('Loading the SQL file into the destination database...')
        destination_subprocess_env = dict(PGPASSWORD=self.destination_config['password'])
        try:
            # execute psql load command
            subprocess.run(
                args=load_command,
                env=destination_subprocess_env,
                check=True
            )
        except subprocess.CalledProcessError as e:
            self.logger.error(f'Error loading the destination database: {e}')
        else:
            self.logger.info('Successfully loaded the destination database')

    def run(self) -> None:
        """
        Run the ELT process by waiting for Postgres to be ready,
        dumping the source database to a SQL file and
        loading the dumped SQL file into the destination database.
        """

        # wait for Postgres to be ready before starting the ELT process
        if not self.__wait_for_postgres(host='source_postgres'):
            exit(1)

        self.logger.info('Starting ELT process...')

        # dump the source database to a SQL file
        dump_command = [
            'pg_dump',
            '-h', self.source_config['host'],
            '-U', self.source_config['user'],
            '-d', self.source_config['dbname'],
            # specify the file name of the SQL script to be executed
            '-f', 'data_dump.sql',
            # don't prompt for password
            '-w'
        ]
        self.__execute_dump_command(dump_command=dump_command)

        # load the dumped SQL file into the destination database
        load_command = [
            'psql',
            '-h', self.destination_config['host'],
            '-U', self.destination_config['user'],
            '-d', self.destination_config['dbname'],
            # enable echoing of all input to the standard output channel
            # equivalent to setting the variable ECHO to all
            '-a',
            '-f', 'data_dump.sql'
        ]
        self.__execute_load_command(load_command=load_command)

        self.logger.info('ELT process completed :)')



if __name__ == '__main__':
    # run the ELT process
    etl = ELT()
    etl.run()