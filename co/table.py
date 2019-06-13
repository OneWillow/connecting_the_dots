import numpy as np
import pandas as pd
import enum
import itertools

class Table(object):
  def __init__(self, n_cols):
    self.n_cols = n_cols
    self.rows = []
    self.aligns = ['r' for c in range(n_cols)]

  def get_cell_align(self, r, c):
    align = self.rows[r].cells[c].align
    if align is None:
      return self.aligns[c]
    else:
      return align

  def add_row(self, row):
    if row.ncols() != self.n_cols:
      raise Exception(f'row has invalid number of cols, {row.ncols()} vs. {self.n_cols}')
    self.rows.append(row)

  def empty_row(self):
    return Row.Empty(self.n_cols)

  def expand_rows(self, n_add_cols=1):
    if n_add_cols < 0: raise Exception('n_add_cols has to be positive')
    self.n_cols += n_add_cols
    for row in self.rows:
      row.cells.extend([Cell() for cidx in range(n_add_cols)])

  def add_block(self, data, row=-1, col=0, fmt=None, expand=False):
    if row < 0: row = len(self.rows)
    while len(self.rows) < row + len(data):
      self.add_row(self.empty_row())
    for r in range(len(data)):
      cols = data[r]
      if col + len(cols) > self.n_cols:
        if expand:
          self.expand_rows(col + len(cols) - self.n_cols)
        else:
          raise Exception('number of cols does not fit in table')
      for c in range(len(cols)):
        self.rows[row+r].cells[col+c] = Cell(data[r][c], fmt)

class Row(object):
  def __init__(self, cells, pre_separator=None, post_separator=None):
    self.cells = cells
    self.pre_separator = pre_separator
    self.post_separator = post_separator

  @classmethod
  def Empty(cls, n_cols):
    return Row([Cell() for c in range(n_cols)])

  def add_cell(self, cell):
    self.cells.append(cell)

  def ncols(self):
    return sum([c.span for c in self.cells])



class Color(object):
  def __init__(self, color=(0,0,0), fmt='rgb'):
    if fmt == 'rgb':
      self.color = color
    elif fmt == 'RGB':
      self.color = tuple(c / 255 for c in color)
    else:
      return Exception('invalid color format')

  def as_rgb(self):
    return self.color

  def as_RGB(self):
    return tuple(int(c * 255) for c in self.color)

  @classmethod
  def rgb(cls, r, g, b):
    return Color(color=(r,g,b), fmt='rgb')

  @classmethod
  def RGB(cls, r, g, b):
    return Color(color=(r,g,b), fmt='RGB')


class CellFormat(object):
  def __init__(self, fmt='%s', fgcolor=None, bgcolor=None, bold=False):
    self.fmt = fmt
    self.fgcolor = fgcolor
    self.bgcolor = bgcolor
    self.bold = bold

class Cell(object):
  def __init__(self, data=None, fmt=None, span=1, align=None):
    self.data = data
    if fmt is None:
      fmt = CellFormat()
    self.fmt = fmt
    self.span = span
    self.align = align

  def __str__(self):
    return self.fmt.fmt % self.data

class Separator(enum.Enum):
  HEAD = 1
  BOTTOM = 2
  INNER = 3


class Renderer(object):
  def __init__(self):
    pass

  def cell_str_len(self, cell):
    return len(str(cell))

  def col_widths(self, table):
    widths = [0 for c in range(table.n_cols)]
    for row in table.rows:
      cidx = 0
      for cell in row.cells:
        if cell.span == 1:
          strlen = self.cell_str_len(cell)
          widths[cidx] = max(widths[cidx], strlen)
        cidx += cell.span
    return widths

  def render(self, table):
    raise NotImplementedError('not implemented')

  def __call__(self, table):
    return self.render(table)

  def render_to_file_comment(self):
    return ''

  def render_to_file(self, path, table):
    txt = self.render(table)
    with open(path, 'w') as fp:
      fp.write(txt)

class TerminalRenderer(Renderer):
  def __init__(self, col_sep=' '):
    super().__init__()
    self.col_sep = col_sep

  def render_cell(self, table, row, col, widths):
    cell = table.rows[row].cells[col]
    str = cell.fmt.fmt % cell.data
    str_width = len(str)
    cell_width = sum([widths[idx] for idx in range(col, col+cell.span)])
    cell_width += len(self.col_sep) * (cell.span - 1)
    if len(str) > cell_width:
      str = str[:cell_width]
    if cell.fmt.bold:
      # str = sty.ef.bold + str + sty.rs.bold_dim
      # str = sty.ef.bold + str + sty.rs.bold
      pass
    if cell.fmt.fgcolor is not None:
      # color = cell.fmt.fgcolor.as_RGB()
      # str = sty.fg(*color) + str + sty.rs.fg
      pass
    if str_width < cell_width:
      n_ws = (cell_width - str_width)
      if table.get_cell_align(row, col) == 'r':
        str = ' '*n_ws + str
      elif table.get_cell_align(row, col) == 'l':
        str = str + ' '*n_ws
      elif table.get_cell_align(row, col) == 'c':
        n_ws1 = n_ws // 2
        n_ws0 = n_ws - n_ws1
        str = ' '*n_ws0 + str + ' '*n_ws1
    if cell.fmt.bgcolor is not None:
      # color = cell.fmt.bgcolor.as_RGB()
      # str = sty.bg(*color) + str + sty.rs.bg
      pass
    return str

  def render_separator(self, separator, tab, col_widths, total_width):
    if separator == Separator.HEAD:
      return '='*total_width
    elif separator == Separator.INNER:
      return '-'*total_width
    elif separator == Separator.BOTTOM:
      return '='*total_width

  def render(self, table):
    widths = self.col_widths(table)
    total_width = sum(widths) + len(self.col_sep) * (table.n_cols - 1)
    lines = []
    for ridx, row in enumerate(table.rows):
      if row.pre_separator is not None:
        sepline = self.render_separator(row.pre_separator, table, widths, total_width)
        if len(sepline) > 0:
          lines.append(sepline)
      line = []
      for cidx, cell in enumerate(row.cells):
        line.append(self.render_cell(table, ridx, cidx, widths))
      lines.append(self.col_sep.join(line))
      if row.post_separator is not None:
        sepline = self.render_separator(row.post_separator, table, widths, total_width)
        if len(sepline) > 0:
          lines.append(sepline)
    return '\n'.join(lines)

class MarkdownRenderer(TerminalRenderer):
  def __init__(self):
    super().__init__(col_sep='|')
    self.printed_color_warning = False

  def print_color_warning(self):
    if not self.printed_color_warning:
      print('[WARNING] MarkdownRenderer does not support color yet')
      self.printed_color_warning = True

  def cell_str_len(self, cell):
    strlen = len(str(cell))
    if cell.fmt.bold:
      strlen += 4
    strlen = max(5, strlen)
    return strlen

  def render_cell(self, table, row, col, widths):
    cell = table.rows[row].cells[col]
    str = cell.fmt.fmt % cell.data
    if cell.fmt.bold:
      str = f'**{str}**'

    str_width = len(str)
    cell_width = sum([widths[idx] for idx in range(col, col+cell.span)])
    cell_width += len(self.col_sep) * (cell.span - 1)
    if len(str) > cell_width:
      str = str[:cell_width]
    else:
      n_ws = (cell_width - str_width)
      if table.get_cell_align(row, col) == 'r':
        str = ' '*n_ws + str
      elif table.get_cell_align(row, col) == 'l':
        str = str + ' '*n_ws
      elif table.get_cell_align(row, col) == 'c':
        n_ws1 = n_ws // 2
        n_ws0 = n_ws - n_ws1
        str = ' '*n_ws0 + str + ' '*n_ws1

    if col == 0: str = self.col_sep + str
    if col == table.n_cols - 1: str += self.col_sep

    if cell.fmt.fgcolor is not None:
      self.print_color_warning()
    if cell.fmt.bgcolor is not None:
      self.print_color_warning()
    return str

  def render_separator(self, separator, tab, widths, total_width):
    sep = ''
    if separator == Separator.INNER:
      sep = self.col_sep
      for idx, width in enumerate(widths):
        csep = '-' * (width - 2)
        if tab.get_cell_align(1, idx) == 'r':
          csep = '-' + csep + ':'
        elif tab.get_cell_align(1, idx) == 'l':
          csep = ':' + csep + '-'
        elif tab.get_cell_align(1, idx) == 'c':
          csep = ':' + csep + ':'
        sep += csep + self.col_sep
    return sep


class LatexRenderer(Renderer):
  def __init__(self):
    super().__init__()

  def render_cell(self, table, row, col):
    cell = table.rows[row].cells[col]
    str = cell.fmt.fmt % cell.data
    if cell.fmt.bold:
      str = '{\\bf '+ str + '}'
    if cell.fmt.fgcolor is not None:
      color = cell.fmt.fgcolor.as_rgb()
      str = f'{{\\color[rgb]{{{color[0]},{color[1]},{color[2]}}} ' + str + '}'
    if cell.fmt.bgcolor is not None:
      color = cell.fmt.bgcolor.as_rgb()
      str = f'\\cellcolor[rgb]{{{color[0]},{color[1]},{color[2]}}} ' + str
    align = table.get_cell_align(row, col)
    if cell.span != 1 or align != table.aligns[col]:
      str = f'\\multicolumn{{{cell.span}}}{{{align}}}{{{str}}}'
    return str

  def render_separator(self, separator):
    if separator == Separator.HEAD:
      return '\\toprule'
    elif separator == Separator.INNER:
      return '\\midrule'
    elif separator == Separator.BOTTOM:
      return '\\bottomrule'

  def render(self, table):
    lines = ['\\begin{tabular}{' + ''.join(table.aligns) + '}']
    for ridx, row in enumerate(table.rows):
      if row.pre_separator is not None:
        lines.append(self.render_separator(row.pre_separator))
      line = []
      for cidx, cell in enumerate(row.cells):
        line.append(self.render_cell(table, ridx, cidx))
      lines.append(' & '.join(line) + ' \\\\')
      if row.post_separator is not None:
        lines.append(self.render_separator(row.post_separator))
    lines.append('\\end{tabular}')
    return '\n'.join(lines)

class HtmlRenderer(Renderer):
  def __init__(self, html_class='result_table'):
    super().__init__()
    self.html_class = html_class

  def render_cell(self, table, row, col):
    cell = table.rows[row].cells[col]
    str = cell.fmt.fmt % cell.data
    styles = []
    if cell.fmt.bold:
      styles.append('font-weight: bold;')
    if cell.fmt.fgcolor is not None:
      color = cell.fmt.fgcolor.as_RGB()
      styles.append(f'color: rgb({color[0]},{color[1]},{color[2]});')
    if cell.fmt.bgcolor is not None:
      color = cell.fmt.bgcolor.as_RGB()
      styles.append(f'background-color: rgb({color[0]},{color[1]},{color[2]});')
    align = table.get_cell_align(row, col)
    if align == 'l': align = 'left'
    elif align == 'r': align = 'right'
    elif align == 'c': align = 'center'
    else: raise Exception('invalid align')
    styles.append(f'text-align: {align};')
    row = table.rows[row]
    if row.pre_separator is not None:
      styles.append(f'border-top: {self.render_separator(row.pre_separator)};')
    if row.post_separator is not None:
        styles.append(f'border-bottom: {self.render_separator(row.post_separator)};')
    style = ' '.join(styles)
    str = f'    <td style="{style}" colspan="{cell.span}">{str}</td>\n'
    return str

  def render_separator(self, separator):
    if separator == Separator.HEAD:
      return '1.5pt solid black'
    elif separator == Separator.INNER:
      return '0.75pt solid black'
    elif separator == Separator.BOTTOM:
      return '1.5pt solid black'

  def render(self, table):
    lines = [f'<table width="100%" style="border-collapse: collapse" class={self.html_class}>']
    for ridx, row in enumerate(table.rows):
      line = [f'  <tr>\n']
      for cidx, cell in enumerate(row.cells):
        line.append(self.render_cell(table, ridx, cidx))
      line.append('  </tr>\n')
      lines.append(' '.join(line))
    lines.append('</table>')
    return '\n'.join(lines)


def pandas_to_table(rowname, colname, valname, data, val_cell_fmt=CellFormat(fmt='%.4f'), best_val_cell_fmt=CellFormat(fmt='%.4f', bold=True), best_is_max=[]):
  rnames = data[rowname].unique()
  cnames = data[colname].unique()
  tab = Table(1+len(cnames))

  header = [Cell('', align='r')]
  header.extend([Cell(h, align='r') for h in cnames])
  header = Row(header, pre_separator=Separator.HEAD, post_separator=Separator.INNER)
  tab.add_row(header)

  for rname in rnames:
    cells = [Cell(rname, align='l')]
    for cname in cnames:
      cdata = data[data[colname] == cname]
      if cname in best_is_max:
        bestval = cdata[valname].max()
        val = cdata[cdata[rowname] == rname][valname].max()
      else:
        bestval = cdata[valname].min()
        val = cdata[cdata[rowname] == rname][valname].min()
      if val == bestval:
        fmt = best_val_cell_fmt
      else:
        fmt = val_cell_fmt
      cells.append(Cell(val, align='r', fmt=fmt))
    tab.add_row(Row(cells))
  tab.rows[-1].post_separator = Separator.BOTTOM
  return tab



if __name__ == '__main__':
  # df = pd.read_pickle('full.df')
  # best_is_max = ['movF0.5', 'movF1.0']
  # tab = pandas_to_table(rowname='method', colname='metric', valname='val', data=df, best_is_max=best_is_max)

  # renderer = TerminalRenderer()
  # print(renderer(tab))

  tab = Table(7)
  # header = Row([Cell('header', span=7, align='c')], pre_separator=Separator.HEAD, post_separator=Separator.INNER)
  # tab.add_row(header)
  # header2 = Row([Cell('thisisaverylongheader', span=4, align='c'), Cell('vals2', span=3, align='c')], post_separator=Separator.INNER)
  # tab.add_row(header2)
  tab.add_row(Row([Cell(f'c{c}') for c in range(7)]))
  tab.rows[-1].post_separator = Separator.INNER
  tab.add_block(np.arange(15*7).reshape(15,7))
  tab.rows[4].cells[2].fmt = CellFormat(bold=True)
  tab.rows[2].cells[1].fmt = CellFormat(fgcolor=Color.rgb(0.2,0.6,0.1))
  tab.rows[2].cells[2].fmt = CellFormat(bgcolor=Color.rgb(0.7,0.1,0.5))
  tab.rows[5].cells[3].fmt = CellFormat(bold=True,bgcolor=Color.rgb(0.7,0.1,0.5),fgcolor=Color.rgb(0.1,0.1,0.1))
  tab.rows[-1].post_separator = Separator.BOTTOM

  renderer = TerminalRenderer()
  print(renderer(tab))
  renderer = MarkdownRenderer()
  print(renderer(tab))

  # renderer = HtmlRenderer()
  # html_tab = renderer(tab)
  # print(html_tab)
  # with open('test.html', 'w') as fp:
  #   fp.write(html_tab)

  # import latex

  # renderer = LatexRenderer()
  # ltx_tab = renderer(tab)
  # print(ltx_tab)

  # with open('test.tex', 'w') as fp:
  #   latex.write_doc_prefix(fp, document_class='article')
  #   fp.write('this is text that should appear before the table and should be long enough to wrap around.\n'*40)
  #   fp.write('\\begin{table}')
  #   fp.write(ltx_tab)
  #   fp.write('\\end{table}')
  #   fp.write('this is text that should appear after the table and should be long enough to wrap around.\n'*40)
  #   latex.write_doc_suffix(fp)
