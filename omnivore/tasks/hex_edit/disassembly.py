import os
import sys
import wx

from atrcopy import match_bit_mask, comment_bit_mask, data_bit_mask, selected_bit_mask

from omnivore.utils.wx.bytegrid import ByteGridTable, ByteGrid, HexTextCtrl, HexCellEditor

from actions import GotoIndexAction
from commands import MiniAssemblerCommand

import logging
log = logging.getLogger(__name__)


class DisassemblyTable(ByteGridTable):
    column_labels = ["Bytes", "Disassembly", "Comment"]
    column_sizes = [8, 12, 20]
    
    def __init__(self):
        ByteGridTable.__init__(self)
        self.lines = []
        self._rows = 0
        self.index_to_row = []
        self.start_addr = 0
        self.next_row = -1
        self.chunk_size = 256
        self.disassembler = None

    def set_editor(self, editor):
        self.editor = editor
        self.segment = segment = self.editor.segment
        self.lines = []
        self.index_to_row = []
        self._rows = 0
        self.disassembler = editor.machine.get_disassembler(editor.task.hex_grid_lower_case, editor.task.assembly_lower_case)
        self.disassembler.set_pc(segment, segment.start_addr)
        self.next_row = 0
        self.start_addr = segment.start_addr
        self.disassemble_next()
    
    def restart_disassembly(self, index):
        try:
            next_row = self.index_to_row[index]
        except IndexError:
            # requesting an index that has yet to be disassembled, so it will
            # get there when it gets there! Be patient!
            return
        
        # don't reset starting point if the requested index is already in the
        # region to be rebuilt
        if self.next_row < 0 or next_row < self.next_row:
            self.next_row = next_row
            pc = self.get_pc(self.next_row)
            self.disassembler.set_pc(self.segment, pc)
    
    def disassemble_next(self):
        if self.next_row < 0:
            return
        lines = []
        start_row = self.next_row
        try:
            for i in range(self.chunk_size):
                (addr, bytes, opstr, comment, flag, dest_pc) = self.disassembler.get_instruction()
                count = len(bytes)
                data = (addr, bytes, opstr, comment, count, flag)
                lines.append(data)
        except StopIteration:
            pass
        if lines:
            n = len(lines)
            self.lines[start_row:start_row+n] = lines
            start_index, index_to_row = self.get_index_to_row(lines, start_row)
            self.index_to_row[start_index:start_index+len(index_to_row)] = index_to_row
            self.next_row += n
        else:
            self.lines[self.next_row:] = []
            self.next_row = -1
    
    def get_index_to_row(self, lines, start_row):
        row = start_row
        index = lines[0][0] - self.start_addr
        counts = [d[4] for d in lines]
        index_to_row = []
        for c in counts:
            index_to_row.extend([row] * c)
            row += 1
        return index, index_to_row
        
    def set_grid_cell_attr(self, grid, col, attr):
        ByteGridTable.set_grid_cell_attr(self, grid, col, attr)
        if col == 1:
            attr.SetReadOnly(False)
        else:
            attr.SetReadOnly(True)
    
    def get_index_range(self, r, c):
        try:
            try:
                line = self.lines[r]
            except:
                line = self.lines[-1]
            index = line[0] - self.start_addr
            return index, index + line[4]
        except IndexError:
            return 0, 0
    
    def is_index_valid(self, index):
        return index < len(self.segment)
    
    def get_row_col(self, index):
        try:
            row = self.index_to_row[index]
        except:
            row = self.index_to_row[-1]
        return row, 1

    def get_next_cursor_pos(self, row, col):
        col += 1
        if col >= self._cols:
            if row < self._rows - 1:
                row += 1
                col = 1
            else:
                col = self._cols - 1
        return (row, col)

    def get_next_editable_pos(self, row, col):
        if col < 1:
            col = 1
        else:
            col = 1
            row += 1
        return (row, col)
   
    def get_prev_cursor_pos(self, row, col):
        col -= 1
        if col < 1:
            if row > 0:
                row -= 1
                col = self._cols - 1
            else:
                col = 1
        return (row, col)
   
    def get_page_index(self, index, segment_page_size, dir, grid):
        r, c = self.get_row_col(index)
        vr = grid.get_num_visible_rows() - 1
        r += (dir * vr)
        if r < 0:
            r = 0
        index, _ = self.get_index_range(r, 0)
        return index
    
    def get_pc(self, row):
        return self.lines[row][0]
    
    def get_addr_dest(self, row):
        index, _ = self.get_index_range(row, 0)
        index_addr = self.get_pc(row)
        d = self.editor.machine.get_disassembler(False, False)
        d.set_pc(self.segment.data[index:], index_addr)
        args = d.disasm()
        return args[-1]

    def get_comments(self, index, line=None):
        if line is None:
            row = self.index_to_row[index]
            line = self.lines[row]
        comments = []
        c = str(line[3])
        if c:
            comments.append(c)
        for i in range(line[4]):
            c = self.segment.get_comment(index + i)
            if c:
                comments.append(c)
        return " ".join(comments)

    def get_value_style_lower(self, row, col):
        line = self.lines[row]
        index = line[0] - self.start_addr
        style = 0
        for i in range(line[4]):
            style |= self.segment.style[index + i]
        if col == 0:
            text = " ".join("%02x" % i for i in line[1])
        elif col == 2 and (style & comment_bit_mask):
            text = self.get_comments(index, line)
        else:
            text = str(line[col + 1])
        return text, style
    
    def get_value_style_upper(self, row, col):
        line = self.lines[row]
        index = line[0] - self.start_addr
        style = 0
        for i in range(line[4]):
            style |= self.segment.style[index + i]
        if col == 0:
            text = " ".join("%02X" % i for i in line[1])
        elif col == 2 and (style & comment_bit_mask):
            text = self.get_comments(index, line)
        else:
            text = str(line[col + 1])
        return text, style
    
    def get_style_override(self, row, col, style):
        if self.lines[row][5]:
            return style|comment_bit_mask
        return style

    def get_label_at_index(self, index):
        row = self.index_to_row[index]
        return self.get_label_at_row(row)
    
    def get_label_at_row(self, row):
        addr = self.get_pc(row)
        if self.get_value_style == self.get_value_style_lower:
            return "%04x" % addr
        return "%04X" % addr

    def GetRowLabelValue(self, row):
        if self.lines:
            return self.get_label_at_row(row)
        return "0000"

    def ResetViewProcessArgs(self, grid, editor, *args):
        if editor is not None:
            self.set_editor(editor)
        else:
            self._rows = len(self.lines)


class AssemblerTextCtrl(HexTextCtrl):
    def setMode(self, mode):
        self.mode='6502'
        self.SetMaxLength(0)
        self.autoadvance=0
        self.userpressed=False

class AssemblerEditor(HexCellEditor):
    def Create(self, parent, id, evtHandler):
        """
        Called to create the control, which must derive from wx.Control.
        *Must Override*
        """
        self._tc = AssemblerTextCtrl(parent, id, self.parentgrid)
        self.SetControl(self._tc)

        if evtHandler:
            self._tc.PushEventHandler(evtHandler)


class DisassemblyPanel(ByteGrid):
    """
    View for editing in hexidecimal notation.
    """
    short_name = "disasm"
    
    # Segment saver interface for menu item display
    export_data_name = "Disassembly"
    export_extensions = [".s"]

    def __init__(self, parent, task, **kwargs):
        """Create the HexEdit viewer
        """
        table = DisassemblyTable()
        ByteGrid.__init__(self, parent, task, table, **kwargs)
        
        # During idle-time disassembly, an index may not yet be visible.  The
        # value is saved here so the view can be scrolled there once it does
        # get disassembled.
        self.pending_index = -1
    
    def get_default_cell_editor(self):
        return AssemblerEditor(self)

    def perform_idle(self):
        if self.table.next_row >= 0:
            self.table.disassemble_next()
            self.table.ResetView(self, None)
            if self.pending_index >= 0:
                self.goto_index(self.pending_index)
    
    def restart_disassembly(self, index):
        self.table.restart_disassembly(index)
    
    def get_disassembled_text(self, start, end):
        """Returns list of lines representing the disassembly
        
        Raises IndexError if the disassembly hasn't reached the index yet
        """
        start_row = self.table.index_to_row[start]
        try:
            end_row = self.table.index_to_row[end]
        except IndexError:
            # check if entire segment selected; if so, end will be one past last
            # allowable entry in index_to_row
            end -= 1
            end_row = self.table.index_to_row[end]
        lines = []
        blank_label = ""
        org = self.table.GetRowLabelValue(start_row)
        lines.append("%-8s%s $%s" % (blank_label, self.table.disassembler.asm_origin, org))
        for row in range(start_row, end_row + 1):
            label = blank_label
            code = self.table.GetValue(row, 1)
            comment = self.table.GetValue(row, 2)
            if comment:
                if not comment.startswith(";"):
                    comment = ";" + comment
                lines.append("%-8s%-12s %s" % (label, code, comment))
            else:
                lines.append("%-8s%s" % (label, code))
        return lines
    
    def encode_data(self, segment):
        """Segment saver interface: take a segment and produce a byte
        representation to save to disk.
        """
        index = len(self.table.index_to_row) - 1
        try:
            lines = self.get_disassembled_text(0, index)
            text = os.linesep.join(lines) + os.linesep
            bytes = text.encode("utf-8")
            return bytes
        except IndexError:
            raise RuntimeError("Disassembly still in progress. Try again in a few seconds.")

    def get_status_message_at_index(self, index, row, col):
        msg = ByteGrid.get_status_message_at_index(self, index, row, col)
        comments = self.table.get_comments(index)
        return "%s  %s" % (msg, comments)

    def goto_index(self, index):
        try:
            row = self.table.index_to_row[index]
            self.pending_index = -1
        except IndexError:
            self.pending_index = index
        else:
            row, col = self.table.get_row_col(index)
            self.SetGridCursor(row, col)
            self.MakeCellVisible(row,col)
        
    def change_value(self, row, col, text):
        """Called after editor has provided a new value for a cell.
        
        Can use this to override the default handler.  Return True if the grid
        should be updated, or False if the value is invalid or the grid will
        be updated some other way.
        """
        try:
            pc = self.table.get_pc(row)
            cmd = text.upper()
            bytes = self.table.disassembler.assemble_text(pc, cmd)
            start, _ = self.table.get_index_range(row, col)
            end = start + len(bytes)
            cmd = MiniAssemblerCommand(self.table.segment, start, end, bytes, cmd)
            self.task.active_editor.process_command(cmd)
            return True
        except RuntimeError, e:
            self.task.window.error(unicode(e))
            self.SetFocus()  # OS X quirk: return focus to the grid so the user can keep typing
        return False
    
    def search(self, search_text, match_case=False):
        lines = self.table.lines
        s = self.table.start_addr
        if not match_case:
            search_text = search_text.lower()
            matches = [(t[0] - s, t[0] - s + len(t[1])) for t in lines if search_text in t[3].lower()]
        else:
            matches = [(t[0] - s, t[0] - s + len(t[1])) for t in lines if search_text in t[3]]
        return matches
    
    def get_goto_action(self, r, c):
        addr_dest = self.table.get_addr_dest(r)
        if addr_dest is not None:
            segment_start = self.table.segment.start_addr
            segment_num = -1
            addr_index = addr_dest - segment_start
            if addr_dest < segment_start or addr_dest > segment_start + len(self.table.segment):
                segment_num, segment_dest, addr_index = self.editor.document.find_segment_in_range(addr_dest)
                if segment_dest is not None:
                    msg = "Go to address $%04x in segment %s" % (addr_dest, str(segment_dest))
                else:
                    msg = "Address $%04x not in any segment" % addr_dest
                    addr_dest = None
            else:
                msg = "Go to address $%04x" % addr_dest
        else:
            msg = "No address to jump to"
        if addr_dest is not None:
            goto_action = GotoIndexAction(name=msg, enabled=True, segment_num=segment_num, addr_index=addr_index, task=self.task, active_editor=self.task.active_editor)
        else:
            goto_action = GotoIndexAction(name=msg, enabled=False, task=self.task)
        return goto_action
    
    def get_popup_actions(self, r, c):
        goto_action = self.get_goto_action(r, c)
        actions = [goto_action, None]
        actions.extend(self.editor.common_popup_actions())
        return actions
