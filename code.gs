
const CONFIG = {
  SPREADSHEET_ID: '1ct8owykbsFzzlvjBHAPk_I44tr9bSbGB5KI4d5jJixo',
  // SHEET_ID: 602738795, // Tháng 10
  SHEET_ID: 1390872491, // Tháng 11
  NAME_COLUMN: 4,
  TITLE_ROW: 2,
  TITLE_COLUMN: 5,
  DATE_HEADER_ROW: 4,
  SHIFT_HEADER_ROW: 5,
  FIRST_DATE_COLUMN: 5,
  COLUMNS_PER_DAY: 5,
  TOTAL_DAYS: 30
};

function doGet() {
  return HtmlService.createHtmlOutputFromFile('Index')
    .setTitle('Tra cứu giờ OT')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

function getOTSummary(targetName) {
  if (!targetName || !targetName.trim()) {
    throw new Error('Vui lòng nhập tên nhân viên.');
  }

  const ss = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID);

  const sheet = ss.getSheets().find(
    s => s.getSheetId() === CONFIG.SHEET_ID
  );

  if (!sheet) {
    throw new Error('Không tìm thấy sheet ID ' + CONFIG.SHEET_ID);
  }

  const lastRow = sheet.getLastRow();
  const lastCol = sheet.getLastColumn();

  if (!lastRow || !lastCol) {
    throw new Error('Google Sheets hiện không có dữ liệu.');
  }

  const data = sheet.getRange(1, 1, lastRow, lastCol)
    .getDisplayValues();

  const backgrounds = sheet.getRange(1, 1, lastRow, lastCol)
    .getBackgrounds();

  const normalize = value => String(value || '')
    .trim()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[đĐ]/g, 'd')
    .toLowerCase()
    .replace(/\s+/g, ' ');

  const matches = [];

  for (let r = CONFIG.SHIFT_HEADER_ROW; r < lastRow; r++) {
    if (
      normalize(data[r][CONFIG.NAME_COLUMN - 1]) ===
      normalize(targetName)
    ) {
      matches.push(r);
    }
  }

  if (matches.length === 0) {
    throw new Error(
      'Không tìm thấy nhân viên "' + targetName + '" trong cột D.'
    );
  }

  if (matches.length > 1) {
    throw new Error(
      'Có nhiều dòng trùng tên "' + targetName + '".'
    );
  }

  const employeeRow = matches[0];

  const title = sheet.getRange(
    CONFIG.TITLE_ROW,
    CONFIG.TITLE_COLUMN
  ).getDisplayValue().trim();

  const titleMatch = title.match(
    /THÁNG\s*(\d{1,2})\s*[\/-]\s*(\d{4})/i
  );

  if (!titleMatch) {
    throw new Error(
      'Không đọc được tháng/năm từ tiêu đề: ' + title
    );
  }

  const month = Number(titleMatch[1]);
  const year = Number(titleMatch[2]);

  if (month < 1 || month > 12 || year < 1900) {
    throw new Error('Tháng/năm không hợp lệ: ' + title);
  }

  const startDate = new Date(year, month - 2, 26);
  const endDate = new Date(year, month - 1, 25);

  // Nhận diện màu nền ca T
  function getColorType(hex) {
    const color = String(hex || '').replace('#', '');

    if (!/^[0-9a-f]{6}$/i.test(color)) return '';

    const r = parseInt(color.substring(0, 2), 16);
    const g = parseInt(color.substring(2, 4), 16);
    const b = parseInt(color.substring(4, 6), 16);

    if (
      r >= 180 &&
      g >= 150 &&
      b <= 150 &&
      r - b >= 60 &&
      g - b >= 40
    ) {
      return 'T';
    }

    if (
      r >= 170 &&
      r - g >= 65 &&
      r - b >= 55 &&
      g <= 175 &&
      b <= 175
    ) {
      return 'N';
    }

    return '';
  }

  // Các mã không tính OT tại ô tương ứng
  function isNoOT(value) {
    const v = String(value || '').trim().toUpperCase();

    return !v ||
      ['X', '-', 'OFF', 'OFF/2', 'CH', 'P'].includes(v) ||
      v.startsWith('CH/');
  }

  // Tính OT từng ca
  function calculateShift(value, header, background) {
    const v = String(value || '').trim().toUpperCase();
    const h = String(header || '').trim().toUpperCase();

    if (isNoOT(v)) return 0;

    if (h === 'S' || h === 'TR') return 1;

    if (h !== 'T') return 0;

    if (v === 'FB' || v.startsWith('FB ')) return 4;
    if (v === 'T') return 3;
    if (v === 'N') return 4;

    const type = getColorType(background);

    if (type === 'T') return 3;
    if (type === 'N') return 4;

    return 0;
  }

  const shiftHeaders = data[CONFIG.SHIFT_HEADER_ROW - 1];
  const dateHeaders = data[CONFIG.DATE_HEADER_ROW - 1];

  const daily = [];
  const seenDates = new Set();

  let totalHours = 0;
  let totalS = 0;
  let totalTR = 0;
  let totalT = 0;

  const timeZone =
    ss.getSpreadsheetTimeZone() || 'Asia/Ho_Chi_Minh';

  const firstColumnIndex = CONFIG.FIRST_DATE_COLUMN - 1;

  const maxDayGroups = Math.min(
    CONFIG.TOTAL_DAYS,
    Math.floor(
      (lastCol - firstColumnIndex) / CONFIG.COLUMNS_PER_DAY
    )
  );

  for (let i = 0; i < maxDayGroups; i++) {
    const c = firstColumnIndex + i * CONFIG.COLUMNS_PER_DAY;

    const rawDay = String(dateHeaders[c] || '').trim();
    const dayNumber = Number(rawDay);

    if (
      !rawDay ||
      !Number.isInteger(dayNumber) ||
      dayNumber < 1 ||
      dayNumber > 31
    ) {
      continue;
    }

    const date = dayNumber >= 26
      ? new Date(year, month - 2, dayNumber)
      : new Date(year, month - 1, dayNumber);

    if (
      date < startDate ||
      date > endDate ||
      date.getDate() !== dayNumber
    ) {
      continue;
    }

    const dateKey = Utilities.formatDate(
      date,
      timeZone,
      'yyyy-MM-dd'
    );

    if (seenDates.has(dateKey)) continue;
    seenDates.add(dateKey);

    const sValue = String(
      data[employeeRow][c] || ''
    ).trim().toUpperCase();

    const hcsValue = String(
      data[employeeRow][c + 1] || ''
    ).trim().toUpperCase();

    const trValue = String(
      data[employeeRow][c + 2] || ''
    ).trim().toUpperCase();

    const hccValue = String(
      data[employeeRow][c + 3] || ''
    ).trim().toUpperCase();

    const tValue = String(
      data[employeeRow][c + 4] || ''
    ).trim().toUpperCase();

    const fourShiftValues = [
      sValue,
      hcsValue,
      trValue,
      hccValue
    ];

    const allFourOff = fourShiftValues.every(
      value => value === 'OFF'
    );

    const isHalfDayOff = ['OFF/2', 'P/2'].includes(hccValue);

    const isCH =
      hcsValue === '' &&
      hccValue !== '' &&
      !allFourOff &&
      !isHalfDayOff;

    // ==================================================
    // NHẬN DIỆN NGHỈ PHÉP P CẢ NGÀY
    // ==================================================

    const fiveShiftValues = [
      sValue,
      hcsValue,
      trValue,
      hccValue,
      tValue
    ];

    const isFullDayLeave = fiveShiftValues.some(
      value => String(value || '').trim().toUpperCase() === 'P'
    );

    // ==================================================

    const shifts = [
      { index: c, label: 'S' },
      { index: c + 2, label: 'TR' },
      { index: c + 4, label: 'T' }
    ];

    const dayItems = [];
    let dayHours = 0;

    shifts.forEach(shift => {
      const value = data[employeeRow][shift.index];
      const header = shiftHeaders[shift.index];
      const background = backgrounds[employeeRow][shift.index];

      if (
        String(header || '').trim().toUpperCase() !== shift.label
      ) {
        return;
      }

      let hours = 0;

      // Nghỉ phép P cả ngày => không tính OT
      if (isFullDayLeave) {
        hours = 0;

      // ca CH
      } else if (shift.label === 'T') {
        if (isCH) {
          hours = 0;
        } else {
          hours = calculateShift(value, header, background);
        }

      // Ca S và TR
      } else {
        hours = calculateShift(value, header, background);
      }

      if (hours > 0) {
        dayItems.push({
          column: shift.label,
          code: String(value).trim(),
          hours: hours
        });

        dayHours += hours;

        if (shift.label === 'S') totalS += hours;
        if (shift.label === 'TR') totalTR += hours;
        if (shift.label === 'T') totalT += hours;
      }
    });

    totalHours += dayHours;

    daily.push({
      date: Utilities.formatDate(date, timeZone, 'dd/MM/yyyy'),
      day: dayNumber,
      shifts: dayItems,
      hours: dayHours
    });
  }

  daily.sort((a, b) => {
    const order = day => day.day >= 26
      ? day.day - 26
      : day.day + 6;

    return order(a.day) - order(b.day);
  });

  return {
    name: data[employeeRow][CONFIG.NAME_COLUMN - 1],
    startDate: Utilities.formatDate(
      startDate,
      timeZone,
      'dd/MM/yyyy'
    ),
    endDate: Utilities.formatDate(
      endDate,
      timeZone,
      'dd/MM/yyyy'
    ),
    totalHours: totalHours,
    totalS: totalS,
    totalTR: totalTR,
    totalT: totalT,
    daily: daily
  };
}

// Tìm kiếm nhân viên
function searchEmployees(keyword) {
  const query = normalizeText(keyword || '');

  if (!query) return [];

  const ss = SpreadsheetApp.openById(CONFIG.SPREADSHEET_ID);
  const sheet = ss.getSheetById(CONFIG.SHEET_ID);

  if (!sheet) {
    throw new Error('Không tìm thấy sheet lịch nhân viên.');
  }

  const lastRow = sheet.getLastRow();

  if (lastRow < 1) return [];

  const values = sheet.getRange(1, 3, lastRow, 2)
    .getDisplayValues();

  return values
    .filter(row => {
      const code = String(row[0] || '').trim();
      const name = String(row[1] || '').trim();

      if (!code || !name) return false;

      const normalizedCode = normalizeText(code);
      const normalizedName = normalizeText(name);

      return normalizedName.includes(query) ||
        normalizedCode.includes(query);
    })
    .map(row => ({
      code: String(row[0]).trim(),
      name: String(row[1]).trim()
    }))
    .slice(0, 15);
}

// Chuẩn hóa chữ tiếng Việt
function normalizeText(value) {
  return String(value || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd')
    .replace(/Đ/g, 'D')
    .toLowerCase()
    .trim();
}
