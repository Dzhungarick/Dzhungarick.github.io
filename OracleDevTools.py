# coding: utf8

'''
      ▄▄▄   ▄▄▄·  ▄▄· ▄▄▌  ▄▄▄ .    ·▄▄▄▄  ▄▄▄ . ▌ ▐·    ▄▄▄▄▄            ▄▄▌  .▄▄ · 
▪     ▀▄ █·▐█ ▀█ ▐█ ▌▪██•  ▀▄.▀·    ██▪ ██ ▀▄.▀·▪█·█▌    •██  ▪     ▪     ██•  ▐█ ▀. 
 ▄█▀▄ ▐▀▀▄ ▄█▀▀█ ██ ▄▄██▪  ▐▀▀▪▄    ▐█· ▐█▌▐▀▀▪▄▐█▐█•     ▐█.▪ ▄█▀▄  ▄█▀▄ ██▪  ▄▀▀▀█▄
▐█▌.▐▌▐█•█▌▐█ ▪▐▌▐███▌▐█▌▐▌▐█▄▄▌    ██. ██ ▐█▄▄▌ ███      ▐█▌·▐█▌.▐▌▐█▌.▐▌▐█▌▐▌▐█▄▪▐█
 ▀█▄▀▪.▀  ▀ ▀  ▀ ·▀▀▀ .▀▀▀  ▀▀▀     ▀▀▀▀▀•  ▀▀▀ . ▀       ▀▀▀  ▀█▄▀▪ ▀█▄▀▪.▀▀▀  ▀▀▀▀ 

'''

import sys
import os
import sublime
import sublime_plugin
import time
from SqlScriptParser import ScriptParser
from OracleSession import OracleSession

session = OracleSession()

#  ▄▄▄ .▐▄• ▄ ▄▄▄ . ▄▄·     .▄▄ · .▄▄▄  ▄▄▌  
#  ▀▄.▀· █▌█▌▪▀▄.▀·▐█ ▌▪    ▐█ ▀. ▐▀•▀█ ██•  
#  ▐▀▀▪▄ ·██· ▐▀▀▪▄██ ▄▄    ▄▀▀▀█▄█▌·.█▌██▪  
#  ▐█▄▄▌▪▐█·█▌▐█▄▄▌▐███▌    ▐█▄▪▐█▐█▪▄█·▐█▌▐▌
#   ▀▀▀ •▀▀ ▀▀ ▀▀▀ ·▀▀▀      ▀▀▀▀ ·▀▀█. .▀▀▀
# Выполнить запрос
# "command": "exec_sql"
class ExecSqlCommand(sublime_plugin.TextCommand):  
    def run(self, edit): 
        view = self.view
        
        region = view.sel()[0]
        if not region.empty():
            selection = view.substr(region)
        else:
            session.ShowError('Необходимо выделить запрос')
            return

        if not session.IsConnected():
            session.ShowError()
            return              
        
        result = session.execute(selection)
        if session.HasError():
            session.ShowError()
            return 

        if result:
            begin_time = time.time()
            session.PutOutputText(session.GetSqlResultAsText(result))
            print(time.time() - begin_time)
        else:
            session.PutOutputText('PL/SQL procedure successfully completed. \n\n')
            if session.dbms_output:
                session.PutOutputText('DBMS OUTPUT :: \n\n')
                session.PutOutputText(session.GetDbmsOutput())

        if not session.OutputIsEmpty():
            session.OutputResult('SQL result')

#  ▄▄▄ .▐▄• ▄ ▄▄▄ . ▄▄·     .▄▄ · .▄▄▄  ▄▄▌      .▄▄ ·  ▄▄· ▄▄▄  ▪   ▄▄▄·▄▄▄▄▄
#  ▀▄.▀· █▌█▌▪▀▄.▀·▐█ ▌▪    ▐█ ▀. ▐▀•▀█ ██•      ▐█ ▀. ▐█ ▌▪▀▄ █·██ ▐█ ▄█•██  
#  ▐▀▀▪▄ ·██· ▐▀▀▪▄██ ▄▄    ▄▀▀▀█▄█▌·.█▌██▪      ▄▀▀▀█▄██ ▄▄▐▀▀▄ ▐█· ██▀· ▐█.▪
#  ▐█▄▄▌▪▐█·█▌▐█▄▄▌▐███▌    ▐█▄▪▐█▐█▪▄█·▐█▌▐▌    ▐█▄▪▐█▐███▌▐█•█▌▐█▌▐█▪·• ▐█▌·
#   ▀▀▀ •▀▀ ▀▀ ▀▀▀ ·▀▀▀      ▀▀▀▀ ·▀▀█. .▀▀▀      ▀▀▀▀ ·▀▀▀ .▀  ▀▀▀▀.▀    ▀▀▀
class SublimeViewEdit:
    def __init__(self):
        self.view = None
        self.edit = None
      
        self.msSpeed = 5
        self.statements = []
        self.statementIndex = 0
        self.offset = 0
        self.stopDelay = False
        self.inUse = False

        self.startTime = None
        self.finishTime = None

sublimeVE = SublimeViewEdit()

def RunScriptMarkStatement(statementIndex,scope='entity'):
    sublimeVE.view.add_regions("statementMark", 
                               [sublime.Region(sublimeVE.statements[statementIndex]['Statement Begin Position']+sublimeVE.offset, 
                                               sublimeVE.statements[statementIndex]['Statement End Position']+sublimeVE.offset)], 
                               scope, 
                               "bookmark", 
                               sublime.DRAW_OUTLINED
                               )
    firstLine = sublimeVE.view.lines(sublimeVE.view.get_regions("statementMark")[0])[0]
    sublimeVE.view.show(firstLine)

# Рекурсивное выполнение sql блоков скрипта
def RunScript():
    def MakeErrorStop(errText,statementText):
        session.PutOutputText('STATEMENT TEXT::' + '\n')
        session.PutOutputText(statementText + '\n')
        session.PutOutputText('ERRORTEXT::' + errText + '\n')

        RunScriptMarkStatement(sublimeVE.statementIndex,'keyword')

        if not sublime.ok_cancel_dialog(errText+'\nContinue?'):
            return True
        return False

    statement = sublimeVE.statements[sublimeVE.statementIndex]
   
    begin_time = time.time()

    result = session.execute(statement['Statement Text'])

    session.PutOutputText('STATEMENT::#' + str(sublimeVE.statementIndex) + '\n')
    session.PutOutputText('START::' + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(begin_time)) + '\n')
    
    if session.HasError():
        if MakeErrorStop(session.sessionError, statement['Statement Text']):
            sublimeVE.stopDelay = True
    else:
        if result:
            session.PutOutputText(session.GetSqlResultAsText(result))
            
            if session.HasError():
                if MakeErrorStop(session.sessionError, statement['Statement Text']):
                    sublimeVE.stopDelay = True
        else:
            session.PutOutputText('completed' + '\n\n')

            if session.dbms_output:
                dbms_output = session.GetDbmsOutput()
                if dbms_output:
                    session.PutOutputText("DBMS OUTPUT :: \n" + dbms_output + '\n')

    end_time = time.time()

    session.PutOutputText('FINISH::' + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time)) + ' ')
    session.PutOutputText('ELAPSED::' + str(round(end_time-begin_time,3)) + '\n\n')

    sublimeVE.statementIndex += 1
    if sublimeVE.statementIndex < len(sublimeVE.statements) and not sublimeVE.stopDelay:
        RunScriptMarkStatement(sublimeVE.statementIndex)

        sublime.set_timeout(RunScript, sublimeVE.msSpeed)
    else:
        sublimeVE.view.erase_regions("statementMark")
        sublimeVE.inUse = False
        sublimeVE.finishTime = time.time()
        session.PutOutputText('START SCRIPT::' + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(sublimeVE.startTime)) + '\n')
        session.PutOutputText('FINISH SCRIPT::' + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(sublimeVE.finishTime)) + '\n')
        session.PutOutputText('FINISH SCRIPT::' + str(round(sublimeVE.finishTime-sublimeVE.startTime,3)))
        session.OutputResult('script result')

# Остановить выполнение скрипта
# "command": "stop_run_script"
class StopRunScriptCommand(sublime_plugin.TextCommand):  
    def run(self, edit):
        sublimeVE.inUse = False
        sublimeVE.stopDelay = True

# Выполнить скрипт
# "command": "exec_sql_script"
class ExecSqlScriptCommand(sublime_plugin.TextCommand):  
    def run(self, edit):
        region = self.view.sel()[0]

        if not region.empty():
            scriptText = self.view.substr(region)
            offset = region.begin()
        else:
            scriptText = self.view.substr(sublime.Region(0, self.view.size()))
            offset = 0

        if not session.IsConnected():
            session.ShowError()
            return        
        
        if sublimeVE.inUse:
            session.ShowError('Script execution in progress\nWait...')
            return

        parser = ScriptParser().LoadScript(scriptText)

        sublimeVE.view = self.view
        sublimeVE.edit = edit
        sublimeVE.statements = parser.SqlStatements
        sublimeVE.statementIndex = 0
        sublimeVE.offset = offset
        sublimeVE.stopDelay = False
        sublimeVE.inUse = True
        sublimeVE.startTime = time.time()
        sublimeVE.finishTime = None

        self.view.erase_regions("checkStatementMark")
        RunScriptMarkStatement(sublimeVE.statementIndex)

        #RunScript()
        sublime.set_timeout(RunScript, sublimeVE.msSpeed)

#  .▄▄ · ▄▄▄ .▄▄▄▄▄▄▄▄▄▄▪   ▐ ▄  ▄▄ • .▄▄ · 
#  ▐█ ▀. ▀▄.▀·•██  •██  ██ •█▌▐█▐█ ▀ ▪▐█ ▀. 
#  ▄▀▀▀█▄▐▀▀▪▄ ▐█.▪ ▐█.▪▐█·▐█▐▐▌▄█ ▀█▄▄▀▀▀█▄
#  ▐█▄▪▐█▐█▄▄▌ ▐█▌· ▐█▌·▐█▌██▐█▌▐█▄▪▐█▐█▄▪▐█
#   ▀▀▀▀  ▀▀▀  ▀▀▀  ▀▀▀ ▀▀▀▀▀ █▪·▀▀▀▀  ▀▀▀▀ 
# Открыть настройки 
# "command": "oracle_dev_tools_settings"
class OracleDevToolsSettingsCommand(sublime_plugin.TextCommand):  
    def run(self, edit):
        self.menu = ['Find object',
                     'Describe',
                     'Explain Plan',
                     'Extract CLOB from SELECT',
                     'Check Script',
                     'Session',
                     'Open settings']
        self.edit = edit
        self.view.window().show_quick_panel(self.menu,self.on_menu_done)

    def on_menu_done(self, index):
        menu = self.menu
        view = self.view

        if index == -1:
            return

        selection = None
        region = view.sel()[0]

        if not region.empty():
            selection = view.substr(region)

        if menu[index] == 'Open settings':
            self.view.window().open_file(os.path.join(sublime.packages_path(), "OracleDevTools", "OracleDevTools.sublime-settings"))
        
        elif menu[index] == 'Find object':
            if not session.IsConnected():
                session.ShowError()
                return
            
            if not selection:
                session.ShowError('Необходимо выделить текст')
                return

            sqlText = '''SELECT OBJECT_NAME, OBJECT_TYPE
                           FROM ALL_OBJECTS
                          WHERE    LOWER (OBJECT_NAME) LIKE LOWER ('%' || :obj_name || '%')
                               AND OWNER IN (USER, 'SYS')
                       GROUP BY OBJECT_NAME, OBJECT_TYPE
                       ORDER BY OBJECT_TYPE, OBJECT_NAME
                      '''
            result = session.execute(sqlText, obj_name = selection)                         
            foundedObjects = [] 

            for row in result.fetchall():
                foundedObjects.append(list(row))

            self.foundedObjects = foundedObjects
            self.view.window().show_quick_panel(foundedObjects, self.on_find_object_done)   
            return
        
        elif menu[index] == 'Session':
            self.sessionMenu = ['Connections',
                                'Reconnect',
                                'Disconnect',
                                'Show current connection string']
            self.view.window().show_quick_panel(self.sessionMenu, self.session_menu_choice)

        elif menu[index] == 'Describe':
            if not session.IsConnected():
                session.ShowError()
                return
            
            if not selection:
                session.ShowError('Необходимо выделить текст')
                return
            
            selection = session.GetObjectName(selection)

            sqlText = ''' SELECT OBJECT_TYPE, OWNER
                            FROM ALL_OBJECTS
                           WHERE LOWER (OBJECT_NAME) = LOWER (:obj_name) AND OWNER IN (USER, 'SYS')             
                      '''
            result = session.execute(sqlText, obj_name = selection)                        
            
            object_type = result.fetchone()
            
            if not object_type:
                # Если не нашли в ALL_OBJECTS, то ищем в списке констрэйнтов
                sqlText = ''' WITH OBJ AS (SELECT LOWER (:obj_name) NAME FROM DUAL)
                              SELECT CASE WHEN CONSTR.TYPE = 'R' THEN 'REF_CONSTRAINT'
                                          ELSE 'CONSTRAINT'
                                     END, 
                                     CONSTR.OWNER
                                FROM (SELECT CONSTRAINTS.OWNER OWNER,
                                             CONSTRAINTS.CONSTRAINT_TYPE TYPE
                                        FROM ALL_CONSTRAINTS CONSTRAINTS, OBJ
                                       WHERE     LOWER (CONSTRAINTS.CONSTRAINT_NAME) = OBJ.NAME
                                             AND CONSTRAINTS.OWNER = USER
                                       UNION ALL
                                      SELECT CONSTRAINTS.OWNER OWNER,
                                             CONSTRAINTS.CONSTRAINT_TYPE TYPE
                                        FROM ALL_CONSTRAINTS CONSTRAINTS, OBJ
                                       WHERE     LOWER (CONSTRAINTS.CONSTRAINT_NAME) = OBJ.NAME
                                             AND CONSTRAINTS.OWNER IN ('SYS')) CONSTR
                          '''
                result = session.execute(sqlText, obj_name = selection)                        
            
                object_type = result.fetchone()
            
            if not object_type:
                session.ShowError('Объект не найден')
                return

            session.PutOutputText('OBJECT NAME :: ' + selection.upper() + '\n')
            session.PutOutputText('OBJECT TYPE :: ' + object_type[0]    + '\n\n')

            if object_type[0] == 'TABLE':
                sqlText = ''' SELECT *
                                FROM ALL_TAB_COMMENTS TAB_COMMENT
                               WHERE LOWER (TAB_COMMENT.TABLE_NAME) = LOWER(:tablename)
                                     AND TAB_COMMENT.OWNER = :tableowner
                          '''
                result = session.execute(sqlText,tablename  = selection, 
                                                 tableowner = object_type[1])
                
                session.PutOutputText(session.GetSqlResultAsText(result))
                
                session.PutOutputText('COLUMNS :: \n')
                sqlText = ''' SELECT CLMN.COLUMN_NAME "Column Name",
                                     CLMN.COLUMN_ID   "ID",
                                     CLMN.DATA_TYPE   "Data Type",
                                     CLMN.NULLABLE    "Nullable",
                                     (SELECT CMMNT.COMMENTS
                                        FROM ALL_COL_COMMENTS CMMNT
                                       WHERE     CMMNT.OWNER = CLMN.OWNER
                                             AND CMMNT.TABLE_NAME = CLMN.TABLE_NAME
                                             AND CMMNT.COLUMN_NAME = CLMN.COLUMN_NAME)
                                     "Comment"
                                FROM ALL_TAB_COLUMNS CLMN
                               WHERE     LOWER(CLMN.TABLE_NAME) = LOWER(:tablename)
                                     AND CLMN.OWNER = :tableowner
                             ORDER BY CLMN.COLUMN_ID
                          '''
                result = session.execute(sqlText,tablename  = selection, 
                                                 tableowner = object_type[1])
                
                session.PutOutputText(session.GetSqlResultAsText(result))

                session.PutOutputText('INDEXES :: \n')
                
                sqlText = ''' SELECT IND_COLUMNS.INDEX_NAME      "Index Name",
                                     INDEXES.UNIQUENESS          "Uniqueness",
                                     INDEXES.DEGREE              "Degree",
                                     IND_COLUMNS.COLUMN_NAME     "Column Name",
                                     IND_COLUMNS.DESCEND         "Order",
                                     IND_COLUMNS.COLUMN_POSITION "Position"
                                FROM ALL_IND_COLUMNS IND_COLUMNS, ALL_INDEXES INDEXES
                               WHERE     IND_COLUMNS.INDEX_NAME = INDEXES.INDEX_NAME
                                     AND LOWER(INDEXES.TABLE_NAME) = LOWER(:tablename)
                                     AND IND_COLUMNS.TABLE_OWNER = INDEXES.TABLE_OWNER
                                     AND INDEXES.TABLE_OWNER = :tableowner
                             ORDER BY IND_COLUMNS.INDEX_NAME, IND_COLUMNS.COLUMN_POSITION
                          ''' 
                result = session.execute(sqlText,tablename  = selection,
                                                 tableowner = object_type[1])
                
                session.PutOutputText(session.GetSqlResultAsText(result))
                session.PutOutputText('CONSTRAINTS :: \n')
                
                sqlText = ''' SELECT CONSTRAINTS.CONSTRAINT_NAME   "Constraint Name",
                                     CONS_COLUMNS.COLUMN_NAME      "Column Name",
                                     CONSTRAINTS.CONSTRAINT_TYPE   "Constraint Type",
                                     CONSTRAINTS.SEARCH_CONDITION  "Search Condition",
                                     CONSTRAINTS.R_CONSTRAINT_NAME "Ref. Constraint Name",
                                     CONSTRAINTS.STATUS            "Status",
                                     CONSTRAINTS.DELETE_RULE       "Delete Rule",
                                     CONSTRAINTS.DEFERRABLE        "Deferrable",
                                     CONSTRAINTS.DEFERRED          "Deferred",
                                     CONSTRAINTS.VALIDATED         "Validated",
                                     CONSTRAINTS.BAD               "Bad",
                                     CONSTRAINTS.RELY              "Rely"
                                FROM ALL_CONSTRAINTS CONSTRAINTS, ALL_CONS_COLUMNS CONS_COLUMNS
                               WHERE     LOWER(CONSTRAINTS.TABLE_NAME) = LOWER(:tablename)
                                     AND CONSTRAINTS.CONSTRAINT_NAME = CONS_COLUMNS.CONSTRAINT_NAME
                                     AND CONSTRAINTS.OWNER = CONS_COLUMNS.OWNER
                                     AND CONSTRAINTS.OWNER = :tableowner
                              ORDER BY CONS_COLUMNS.POSITION
                          '''
                result = session.execute(sqlText,tablename  = selection,
                                                 tableowner = object_type[1])
                
                session.PutOutputText(session.GetSqlResultAsText(result))
                session.PutOutputText('TRIGGERS :: \n')

                sqlText = ''' SELECT TRIGGER_NAME      "Trigger Name",
                                     TRIGGER_TYPE      "Trigger Type",
                                     STATUS            "Status",
                                     TRIGGERING_EVENT  "Triggering Event",
                                     WHEN_CLAUSE       "When Clause"
                                FROM ALL_TRIGGERS
                               WHERE     LOWER(TABLE_NAME) = LOWER(:tablename)
                                     AND TABLE_OWNER = :tableowner
                          '''   
                result = session.execute(sqlText,tablename  = selection,
                                                 tableowner = object_type[1])
                
                session.PutOutputText(session.GetSqlResultAsText(result))
            
            elif object_type[0] == 'VIEW':
                session.PutOutputText('COLUMNS :: \n')
                
                sqlText = ''' SELECT COLUMN_NAME "Column Name",
                                     COLUMN_ID   "ID",
                                     DATA_TYPE   "Data Type",
                                     NULLABLE    "Nullable"
                                FROM ALL_TAB_COLUMNS
                               WHERE     LOWER(TABLE_NAME) = LOWER(:view_name)
                                     AND OWNER = :view_owner
                             ORDER BY COLUMN_ID
                          '''
                result = session.execute(sqlText,view_name  = selection, 
                                                 view_owner = object_type[1])
                
                session.PutOutputText(session.GetSqlResultAsText(result))
                session.PutOutputText('DDL :: \n')
                session.PutOutputText(session.GetObjectDDL(selection, 'VIEW', object_type[1]))

            elif object_type[0] == 'TRIGGER':               
                session.PutOutputText('DESCRIPTION :: \n')
                session.PutOutputText(session.GetObjectDescr(selection, 'TRIGGER', object_type[1]))

                sqlText = ''' SELECT TRIGGER_NAME     "Trigger Name",
                                     TRIGGER_TYPE     "Trigger Type",
                                     TABLE_NAME       "Table Name",
                                     STATUS           "Status",
                                     TRIGGERING_EVENT "Triggering Event",
                                     WHEN_CLAUSE      "When Clause"
                                FROM USER_TRIGGERS
                               WHERE LOWER(TRIGGER_NAME) = LOWER(:triggername)
                          '''
                result = session.execute(sqlText,triggername = selection)
                
                session.PutOutputText(session.GetSqlResultAsText(result))

                session.PutOutputText('ERRORS :: \n')
                session.PutOutputText(session.GetObjectErrors(selection, 'TRIGGER', object_type[1]))
                session.PutOutputText('DDL :: \n')
                session.PutOutputText(session.GetObjectDDL(selection, 'TRIGGER', object_type[1]))

            elif object_type[0] == 'PACKAGE' or object_type[0] == 'PACKAGE BODY':                   
                session.PutOutputText('DESCRIPTION :: \n')
                session.PutOutputText(session.GetObjectDescr(selection, 'PACKAGE', object_type[1]))
                session.PutOutputText(session.GetObjectDescr(selection, 'PACKAGE BODY', object_type[1]))
                session.PutOutputText(session.GetObjectArguments(selection, 'PACKAGE', object_type[1]))
                session.PutOutputText('ERRORS :: \n')
                session.PutOutputText(session.GetObjectErrors(selection, 'PACKAGE', object_type[1]))
                session.PutOutputText(session.GetObjectErrors(selection, 'PACKAGE BODY', object_type[1]))
                session.PutOutputText('DDL :: \n')
                session.PutOutputText(session.GetObjectDDL(selection, 'PACKAGE', object_type[1]))
                
            elif object_type[0] == 'FUNCTION':
                session.PutOutputText('DESCRIPTION :: \n')
                session.PutOutputText(session.GetObjectDescr(selection, 'FUNCTION', object_type[1]))
                session.PutOutputText('ERRORS :: \n')
                session.PutOutputText(session.GetObjectErrors(selection, 'FUNCTION', object_type[1]))
                session.PutOutputText('DDL :: \n')
                session.PutOutputText(session.GetObjectDDL(selection, 'FUNCTION', object_type[1]))
                
            elif object_type[0] == 'PROCEDURE':
                session.PutOutputText('DESCRIPTION :: \n')
                session.PutOutputText(session.GetObjectDescr(selection, 'PROCEDURE', object_type[1]))
                session.PutOutputText('ERRORS :: \n')
                session.PutOutputText(session.GetObjectErrors(selection, 'PROCEDURE', object_type[1]))
                session.PutOutputText('DDL :: \n')
                session.PutOutputText(session.GetObjectDDL(selection, 'PROCEDURE', object_type[1]))

            elif object_type[0] == 'INDEX':
                session.PutOutputText('DESCRIPTION :: \n')
                session.PutOutputText(session.GetObjectDescr(selection, 'INDEX', object_type[1]))

                sqlText = ''' SELECT IND_COLUMNS.COLUMN_NAME     "Column Name",
                                     INDEXES.UNIQUENESS          "Uniqueness",
                                     INDEXES.DEGREE              "Degree",                                           
                                     IND_COLUMNS.DESCEND         "Order",
                                     IND_COLUMNS.COLUMN_POSITION "Position"
                                FROM ALL_IND_COLUMNS IND_COLUMNS, ALL_INDEXES INDEXES
                               WHERE     IND_COLUMNS.INDEX_NAME = INDEXES.INDEX_NAME
                                     AND LOWER(INDEXES.INDEX_NAME) = LOWER(:indexname)
                                     AND IND_COLUMNS.TABLE_OWNER = INDEXES.TABLE_OWNER
                                     AND INDEXES.TABLE_OWNER = :indexowner
                             ORDER BY IND_COLUMNS.INDEX_NAME, IND_COLUMNS.COLUMN_POSITION
                          ''' 
                result = session.execute(sqlText,indexname  = selection,
                                                 indexowner = object_type[1])
                
                session.PutOutputText(session.GetSqlResultAsText(result))
                session.PutOutputText('DDL :: \n')
                session.PutOutputText(session.GetObjectDDL(selection, 'INDEX', object_type[1]))
                
            elif object_type[0] in ['CONSTRAINT','REF_CONSTRAINT']:
                session.PutOutputText('DESCRIPTION :: \n')
                sqlText = ''' SELECT CONSTRAINTS.CONSTRAINT_NAME   "Constraint Name",
                                     CONSTRAINTS.TABLE_NAME        "Table Name",
                                     CONS_COLUMNS.COLUMN_NAME      "Column Name",
                                     CONSTRAINTS.CONSTRAINT_TYPE   "Constraint Type",
                                     CONSTRAINTS.SEARCH_CONDITION  "Search Condition",
                                     CONSTRAINTS.R_CONSTRAINT_NAME "Ref. Constraint Name",
                                     CONSTRAINTS.STATUS            "Status",
                                     CONSTRAINTS.DELETE_RULE       "Delete Rule",
                                     CONSTRAINTS.DEFERRABLE        "Deferrable",
                                     CONSTRAINTS.DEFERRED          "Deferred",
                                     CONSTRAINTS.VALIDATED         "Validated",
                                     CONSTRAINTS.BAD               "Bad",
                                     CONSTRAINTS.RELY              "Rely"
                                FROM ALL_CONSTRAINTS CONSTRAINTS, ALL_CONS_COLUMNS CONS_COLUMNS
                               WHERE     LOWER(CONSTRAINTS.CONSTRAINT_NAME) = LOWER(:constrname)
                                     AND CONSTRAINTS.CONSTRAINT_NAME = CONS_COLUMNS.CONSTRAINT_NAME
                                     AND CONSTRAINTS.OWNER = CONS_COLUMNS.OWNER
                                     AND CONSTRAINTS.OWNER = :constrowner
                              ORDER BY CONS_COLUMNS.POSITION
                          '''
                result = session.execute(sqlText,constrname  = selection,
                                                 constrowner = object_type[1])
                
                session.PutOutputText(session.GetSqlResultAsText(result))
                session.PutOutputText('DDL :: \n')
                session.PutOutputText(session.GetObjectDDL(selection, object_type[0], object_type[1]))
                if session.HasError():
                    session.ShowError()
            else:
                session.PutOutputText('DESCRIPTION :: \n')
                session.PutOutputText(session.GetObjectDescr(selection, object_type[0], object_type[1]))
                session.PutOutputText('DDL :: \n')
                session.PutOutputText(session.GetObjectDDL(selection, object_type[0], object_type[1]))
            
            if not session.OutputIsEmpty():
                session.OutputResult(selection)

        elif menu[index] == 'Extract CLOB from SELECT':
            if not session.IsConnected():
                session.ShowError()
                return
            
            if not selection:
                session.ShowError('Необходимо выделить текст')
                return

            result = session.execute(selection)
            if session.HasError():
                session.ShowError()
                return
            else:
                if result:
                    # Почему-то если извлекать больше 50 строк, то возникает ошибка:
                    # cx_Oracle.ProgrammingError: LOB variable no longer valid after subsequent fetch
                    for index_j, row in enumerate(result.fetchmany(session.maxRows if session.maxRows <= 50 else 50)):
                        for index_i, value in enumerate(row):
                            if session.IsLobValue(value):
                                session.PutOutputText(result.description[index_i][0] + ' :: ROWNUM :: ' + str(index_j) + '\n')
                                session.PutOutputText('-'*len(result.description[index_i][0]) + '\n')
                                session.PutOutputText(value.read().decode(session.encoding) + '\n')
                                session.PutOutputText('-'*len(value.read().decode(session.encoding)) + '\n\n')
                
                if not session.OutputIsEmpty():
                    session.OutputResult('Extract LOB')
                else:
                    session.ShowError('No Clob')
        
        # TODO: dbms_metadata.get_ddl
        elif menu[index] == 'Get script for object':
            if not session.IsConnected():
                session.ShowError()
                return

            object_type = session.GetObjectType(selection)
            print(object_type)
            pass

        elif menu[index] == 'Explain Plan':
            if not session.IsConnected():
                session.ShowError()
                return
            
            if not selection:
                session.ShowError('Необходимо выделить запрос')
                return
            
            sqlText = 'EXPLAIN PLAN FOR ' + selection

            result = session.execute(sqlText)
            if session.HasError():
                session.ShowError()
                return
            
            sqlText = 'SELECT PLAN_TABLE_OUTPUT FROM TABLE(DBMS_XPLAN.DISPLAY(FORMAT=>\'ALL\'))'

            result = session.execute(sqlText)
            if session.HasError():
                session.ShowError()
                return

            session.PutOutputText('STATEMENT ::  \n')
            session.PutOutputText(selection + '\n\n')
            session.PutOutputText('PLAN ::       \n')
            
            for row in result.fetchall():
                session.PutOutputText(row[0] + '\n')

            session.OutputResult('EXPLAIN PLAN')                    

        elif menu[index] == 'Check Script':
            region = view.sel()[0]

            if not region.empty():
                scriptText = view.substr(region)
            else:
                scriptText = view.substr(sublime.Region(0, view.size()))

            outWindow = view.window().new_file()
            outWindow.insert(self.edit,0,scriptText)
            outWindow.set_name('Parsed Script')

            parser = ScriptParser().LoadScript(scriptText)
            regions = []

            for index, statement in enumerate(parser.SqlStatements):
                regions.append(sublime.Region(statement['Statement Begin Position'], statement['Statement End Position']))
            
            outWindow.add_regions("checkStatementMark", 
                                  regions, 
                                  "entity", 
                                  "bookmark", 
                                  sublime.DRAW_OUTLINED)

    def on_find_object_done(self, index):
        if index == -1:
            return
        else:
            self.view.replace(self.edit, self.view.sel()[0], self.foundedObjects[index][0])

    def session_menu_choice(self, index):
        if index == -1:
            return
        
        menu = self.sessionMenu
        
        if menu[index] == 'Reconnect':
            session.Reconnect()
        
        elif menu[index] == 'Disconnect':
            session.Disconnect()
        
        elif menu[index] == 'Connections':
            self.connections = session.GetConnectionsList()
            self.view.window().show_quick_panel(self.connections, self.connection_choice)

        elif menu[index] == 'Show current connection string':
            session.ShowCurrentConnection()

    def connection_choice(self, index):
        if index == -1:
            return
        
        session.Reconnect(self.connections[index][0])
