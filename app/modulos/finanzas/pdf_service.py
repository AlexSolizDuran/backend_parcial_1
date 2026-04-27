from io import BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from typing import List, Optional
from app.modulos.finanzas.model import Pago
from app.modulos.asignacion.model import Asignacion
from app.modulos.incidentes.models.incidente import Incidente
from app.modulos.usuarios.models.usuario import Usuario
from app.modulos.activos.models.taller import Taller


class PagoPDFService:
    """Service for generating PDF reports of payments"""
    
    @staticmethod
    def generar_reporte_pagos_taller(db_session, taller_id: int, 
                                   fecha_desde: Optional[datetime] = None,
                                   fecha_hasta: Optional[datetime] = None) -> BytesIO:
        """
        Genera un PDF con el reporte de pagos de un taller
        
        Args:
            db_session: Sesión de base de datos
            taller_id: ID del taller
            fecha_desde: Fecha inicial (opcional)
            fecha_hasta: Fecha final (opcional)
            
        Returns:
            BytesIO: Buffer con el PDF generado
        """
        
        # Obtener información del taller
        taller = db_session.query(Taller).filter(Taller.id == taller_id).first()
        if not taller:
            raise ValueError(f"Taller con ID {taller_id} no encontrado")
        
        # Construir consulta de pagos
        query = db_session.query(Pago).join(Asignacion, Pago.asignacion_id == Asignacion.id)\
            .filter(Asignacion.taller_id == taller_id)
        
        # Aplicar filtros de fecha si se especifican
        if fecha_desde:
            query = query.filter(Pago.fecha_creacion >= fecha_desde)
        if fecha_hasta:
            query = query.filter(Pago.fecha_creacion <= fecha_hasta)
            
        pagos = query.order_by(Pago.fecha_creacion.desc()).all()
        
        # Obtener información relacionada para cada pago
        pagos_detalle = []
        for pago in pagos:
            asignacion = db_session.query(Asignacion).filter(Asignacion.id == pago.asignacion_id).first()
            incidente = None
            cliente = None
            if asignacion:
                incidente = db_session.query(Incidente).filter(Incidente.id == asignacion.incidente_id).first()
                if incidente:
                    cliente = db_session.query(Usuario).filter(Usuario.id == incidente.cliente_id).first()
            
            pagos_detalle.append({
                'pago': pago,
                'asignacion': asignacion,
                'incidente': incidente,
                'cliente': cliente
            })
        
        # Crear buffer para el PDF
        buffer = BytesIO()
        
        # Crear el documento PDF
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                              rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)
        
        # Contenedor para los elementos del PDF
        story = []
        
        # Estilos
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=20,
            alignment=TA_LEFT,
            textColor=colors.darkgreen
        )
        
        normal_style = styles['Normal']
        normal_style.fontSize = 10
        
        # Título del documento
        story.append(Paragraph("REPORTE DE PAGOS DEL TALLER", title_style))
        story.append(Spacer(1, 12))
        
        # Información del taller
        story.append(Paragraph(f"<b>Taller:</em> {taller.nombre}", normal_style))
        story.append(Paragraph(f"<b>Propietario:</em> {taller.usuario.nombre if taller.usuario else 'N/A'}", normal_style))
        story.append(Paragraph(f"<b>Teléfono:</em> {taller.telefono or 'N/A'}", normal_style))
        story.append(Paragraph(f"<b>Dirección:</em> {taller.direccion or 'N/A'}", normal_style))
        story.append(Spacer(1, 20))
        
        # Filtros aplicados
        if fecha_desde or fecha_hasta:
            filtros_texto = "Período: "
            if fecha_desde:
                filtros_texto += f"Desde {fecha_desde.strftime('%d/%m/%Y')}"
            if fecha_hasta:
                if fecha_desde:
                    filtros_texto += " a "
                filtros_texto += f"Hasta {fecha_hasta.strftime('%d/%m/%Y')}"
            story.append(Paragraph(filtros_texto, normal_style))
            story.append(Spacer(1, 12))
        
        story.append(Spacer(1, 20))
        
        # Estadísticas generales
        total_pagos = len(pagos_detalle)
        total_monto = sum(p['pago'].monto_total for p in pagos_detalle)
        total_comision = sum(p['pago'].monto_comision for p in pagos_detalle)
        pagos_aprobados = len([p for p in pagos_detalle if p['pago'].estado])
        pagos_pendientes = total_pagos - pagos_aprobados
        
        story.append(Paragraph("RESUMEN GENERAL", subtitle_style))
        
        resumen_data = [
            ["Concepto", "Valor"],
            ["Total de Pagos", str(total_pagos)],
            ["Pagos Aprobados", str(pagos_aprobados)],
            ["Pagos Pendientes", str(pagos_pendientes)],
            ["Monto Total Recibido", f"Bs {total_monto:.2f}"],
            ["Comisión Total", f"Bs {total_comision:.2f}"],
            ["Monto Neto", f"Bs {(total_monto - total_comision):.2f}"]
        ]
        
        resumen_table = Table(resumen_data, colWidths=[3*inch, 2*inch])
        resumen_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(resumen_table)
        story.append(Spacer(1, 30))
        
        # Detalle de pagos
        if pagos_detalle:
            story.append(Paragraph("DETALLE DE PAGOS", subtitle_style))
            
            # Cabecera de la tabla
            detalle_data = [["Fecha", "Incidente", "Cliente", "Monto", "Comisión", "Estado"]]
            
            for pago_info in pagos_detalle:
                pago = pago_info['pago']
                incidente = pago_info['incidente']
                cliente = pago_info['cliente']
                
                fecha = pago.fecha_creacion.strftime('%d/%m/%Y') if pago.fecha_creacion else 'N/A'
                incidente_desc = f"#{incidente.id}" if incidente else "N/A"
                cliente_nombre = cliente.nombre if cliente else "N/A"
                monto = f"Bs {pago.monto_total:.2f}"
                comision = f"Bs {pago.monto_comision:.2f}"
                estado = "Aprobado" if pago.estado else "Pendiente"
                
                detalle_data.append([fecha, incidente_desc, cliente_nombre, monto, comision, estado])
            
            detalle_table = Table(detalle_data, colWidths=[1*inch, 1*inch, 1.5*inch, 1*inch, 1*inch, 1*inch])
            detalle_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
            ]))
            
            story.append(detalle_table)
        else:
            story.append(Paragraph("No se encontraron pagos para el período especificado.", normal_style))
        
        # Pie de página
        story.append(Spacer(1, 30))
        story.append(Paragraph(f"Reporte generado el {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", 
                             ParagraphStyle('Footer', parent=normal_style, fontSize=8, textColor=colors.grey)))
        
        # Construir el PDF
        doc.build(story)
        buffer.seek(0)
        
        return buffer