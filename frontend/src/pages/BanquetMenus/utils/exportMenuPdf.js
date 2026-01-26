import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';

/**
 * Export banquet menu to PDF
 * Creates a clean, printable document with menu info and prep items
 */
export function exportMenuToPdf(menu, menuCost, guestCount) {
  const doc = new jsPDF();
  const pageWidth = doc.internal.pageSize.getWidth();
  let yPos = 20;

  // Title
  doc.setFontSize(18);
  doc.setFont('helvetica', 'bold');
  doc.text(menu.name, pageWidth / 2, yPos, { align: 'center' });
  yPos += 10;

  // Subtitle - meal period and service type
  doc.setFontSize(11);
  doc.setFont('helvetica', 'normal');
  doc.text(`${menu.meal_period} - ${menu.service_type}`, pageWidth / 2, yPos, { align: 'center' });
  yPos += 15;

  // Summary info box
  doc.setFontSize(10);
  const summaryData = [
    ['Guest Count', guestCount || 0],
    ['Menu Price', `$${(menu.price_per_person || 0).toFixed(2)}/pp`],
    ['Menu Cost', `$${(menuCost?.menu_cost_per_guest || 0).toFixed(2)}/pp`],
    ['Target FC%', `${(menu.target_food_cost_pct || 0).toFixed(1)}%`],
    ['Actual FC%', `${(menuCost?.actual_food_cost_pct || 0).toFixed(1)}%`],
  ];

  autoTable(doc, {
    startY: yPos,
    head: [],
    body: summaryData,
    theme: 'plain',
    styles: { fontSize: 10, cellPadding: 2 },
    columnStyles: {
      0: { fontStyle: 'bold', cellWidth: 30 },
      1: { cellWidth: 35 }
    },
    margin: { left: 15 },
    tableWidth: 70
  });

  yPos = doc.lastAutoTable.finalY + 15;

  // Menu Items
  const menuItems = menu.menu_items || [];

  menuItems.forEach((item, index) => {
    // Check if we need a new page
    if (yPos > 250) {
      doc.addPage();
      yPos = 20;
    }

    // Menu item header
    doc.setFontSize(12);
    doc.setFont('helvetica', 'bold');
    const itemLabel = item.is_enhancement ? `${item.name} (Enhancement)` : item.name;
    doc.text(itemLabel, 15, yPos);

    // Item cost on the right
    const itemCost = menuCost?.item_costs?.find(c => c.menu_item_id === item.id);
    if (itemCost) {
      doc.setFontSize(10);
      doc.setFont('helvetica', 'normal');
      doc.text(`$${itemCost.cost_per_guest.toFixed(2)}/guest`, pageWidth - 15, yPos, { align: 'right' });
    }
    yPos += 6;

    // Prep items table
    const prepItems = item.prep_items || [];
    if (prepItems.length > 0) {
      const prepCosts = itemCost?.prep_costs || [];

      const tableData = prepItems.map(prep => {
        const prepCost = prepCosts.find(c => c.prep_item_id === prep.id);
        const unitAbbr = prep.unit_abbr || prep.amount_unit || '';
        const guestsPerAmount = prep.guests_per_amount || 1;
        const perLabel = guestsPerAmount === 1 ? '/pp' : `/${guestsPerAmount}`;

        return [
          prep.name,
          `${prep.amount_per_guest || '--'} ${unitAbbr} ${perLabel}`,
          prepCost ? `${prepCost.calculated_amount.toFixed(1)} ${unitAbbr}` : '--',
          prep.common_product_name || prep.product_name || prep.recipe_name || '--',
          prepCost ? `$${prepCost.unit_cost.toFixed(2)}` : '--',
          prepCost ? `$${prepCost.total_cost.toFixed(2)}` : '--',
          '' // Notes column
        ];
      });

      autoTable(doc, {
        startY: yPos,
        head: [['Prep Item', 'Amount', 'Qty Req', 'Linked To', 'Unit $', 'Total', 'Notes']],
        body: tableData,
        theme: 'grid',
        styles: {
          fontSize: 8,
          cellPadding: 3,
        },
        headStyles: {
          fillColor: [60, 60, 60],
          textColor: 255,
          fontStyle: 'bold',
          fontSize: 8
        },
        columnStyles: {
          0: { cellWidth: 35 },  // Prep Item
          1: { cellWidth: 25 },  // Amount
          2: { cellWidth: 22 },  // Qty Req
          3: { cellWidth: 30 },  // Linked To
          4: { cellWidth: 18, halign: 'right' },  // Unit $
          5: { cellWidth: 18, halign: 'right' },  // Total
          6: { cellWidth: 32 }   // Notes - extra space for writing
        },
        margin: { left: 15, right: 15 }
      });

      yPos = doc.lastAutoTable.finalY + 12;
    } else {
      // No prep items
      doc.setFontSize(9);
      doc.setFont('helvetica', 'italic');
      doc.setTextColor(128);
      doc.text('No prep items', 20, yPos);
      doc.setTextColor(0);
      yPos += 10;
    }
  });

  // Footer with date
  const totalPages = doc.internal.getNumberOfPages();
  for (let i = 1; i <= totalPages; i++) {
    doc.setPage(i);
    doc.setFontSize(8);
    doc.setFont('helvetica', 'normal');
    doc.setTextColor(128);
    const date = new Date().toLocaleDateString();
    doc.text(`Generated: ${date}`, 15, doc.internal.pageSize.getHeight() - 10);
    doc.text(`Page ${i} of ${totalPages}`, pageWidth - 15, doc.internal.pageSize.getHeight() - 10, { align: 'right' });
  }

  // Generate filename
  const safeName = menu.name.replace(/[^a-z0-9]/gi, '_').toLowerCase();
  const filename = `${safeName}_${guestCount || 0}guests.pdf`;

  // Save
  doc.save(filename);
}
