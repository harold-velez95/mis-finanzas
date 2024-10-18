function confirmar() {
  document.getElementById('modal').style.display = 'inherit';
  document.getElementById('data').style.display = 'none';
  document.getElementById('botones').style.display = 'none';
}

function editar() {
  document.getElementById('formparcelas').style.display = 'inherit';
  document.getElementById('data').style.display = 'none';
  document.getElementById('botones').style.display = 'none';
  document.getElementById('crear-parcela').style.display = 'none';
}

function añadir() {
  document.getElementById('info_patrimonio').style.display = 'none';
  document.getElementById('añadir').style.display = 'none';
  document.getElementById('formparcelas').style.display = 'inherit';
}

function entradas(){
  var elemento= document.getElementById('salidas');
  var elemento_2= document.getElementById('entradas');
  var elemento_3= document.getElementById('select_descripcion');
  var elemento_4= document.getElementById('select_concepto');
  var elemento_5= document.getElementById('select_entrada');
  var elemento_6= document.getElementById('select_ingreso');
  if (document.getElementById('salida').checked){
    elemento_2.style.display="none";
    elemento.style.display='inherit';
    elemento_3.disabled=false;
    elemento_4.disabled=false;
    elemento_5.disabled=true;
    elemento_6.disabled=true;
  }else{
    elemento_2.style.display="inherit";
    elemento.style.display='none';
    elemento_3.disabled=true;
    elemento_4.disabled=true;
    elemento_5.disabled=false;
    elemento_6.disabled=false;
  }
}

function mostrarInfo() {
    const year = document.getElementById('year').value;
    const month = document.getElementById('month').value;

    // Ocultar todos los divs de información
    for (let i = 1; i <= 12; i++) {
        document.getElementById(`info_${i}`).style.display = 'none';
    }

    // Mostrar el div correspondiente al mes seleccionado
    document.getElementById(`info_${month}`).style.display = 'block';
}

