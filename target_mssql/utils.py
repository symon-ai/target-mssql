import traceback
import logging
import json

class SymonException(Exception):
    def __init__(self, message, code, details=None):
        super().__init__(message)
        self.code = code
        self.details = details

def raise_error(error_info, config):
    error_file_path = config.get('error_file_path', None)
    if error_file_path is not None:
        try:
            with open(error_file_path, 'w', encoding='utf-8') as fp:
                json.dump(error_info, fp)
        except:
            pass

    error_info_json = json.dumps(error_info)
    error_start_marker = config.get('error_start_marker', '[target_error_start]')
    error_end_marker = config.get('error_end_marker', '[target_error_end]')
    logger = logging.getLogger(__name__)
    logger.info(f'{error_start_marker}{error_info_json}{error_end_marker}')

    raise SymonException(error_info.get('message'), error_info.get('code'))

def generate_error_message(e, details=None, parsed=None):
    msg = parsed if parsed is not None else str(e)
    error_code_map = {
        'OperationalError': 'MsSqlOperationalError',
        'IntegrityError': 'MsSqlIntegrityError'
    }
    error_info = {
        'message': msg,
        'code': error_code_map.get(type(e).__name__, type(e).__name__),
        'traceback': traceback.format_exc()
    }
    
    if details is not None:
        error_info['details'] = details
    
    return error_info

def process_error_info(error_info, config):
    if error_info is not None:
        error_file_path = config.get('error_file_path', None)
        if error_file_path is not None:
            try:
                with open(error_file_path, 'w', encoding='utf-8') as fp:
                    json.dump(error_info, fp)
            except:
                pass

        error_info_json = json.dumps(error_info)
        error_start_marker = config.get('error_start_marker', '[target_error_start]')
        error_end_marker = config.get('error_end_marker', '[target_error_end]')
        logger = logging.getLogger(__name__)
        logger.info(f'{error_start_marker}{error_info_json}{error_end_marker}')